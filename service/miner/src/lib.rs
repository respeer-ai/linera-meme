mod command;
mod errors;
mod options;

use std::{str::FromStr, sync::Arc, time::Instant};

use abi::proxy::ProxyAbi;
use async_graphql::{Request, Value, Variables};
use errors::MemeMinerError;
use futures::{lock::Mutex, FutureExt as _};
use linera_base::{
    crypto::CryptoHash,
    identifiers::{Account, ApplicationId, ChainId},
};
use linera_client::chain_listener::{ChainListener, ChainListenerConfig, ClientContext};
use linera_core::{data_types::ClientOutcome, Wallet};
use linera_execution::{Query, QueryOutcome, QueryResponse};
use linera_service::util;
use serde::{de::DeserializeOwned, Deserialize};
use tokio::sync::Notify;
use tokio_util::sync::CancellationToken;

#[derive(Debug, Deserialize)]
struct CreatorChainIdResponse {
    #[serde(alias = "creatorChainId")]
    creator_chain_id: ChainId,
}

#[derive(Debug, Deserialize)]
struct MinerRegisteredResponse {
    #[serde(alias = "minerRegistered")]
    miner_registered: bool,
}

#[derive(Debug, Deserialize)]
struct RegisterMinerResponse {
    #[serde(alias = "registerMiner")]
    register_miner: Vec<u8>,
}

#[derive(Debug, Deserialize)]
struct Response<T> {
    data: T,
}

pub struct MemeMiner<C>
where
    C: ClientContext,
{
    context: Arc<Mutex<C>>,
    storage: <C::Environment as linera_core::Environment>::Storage,

    meme_proxy_application_id: ApplicationId,

    new_block_notifier: Arc<Notify>,
    pub chain_listener_config: ChainListenerConfig,

    default_chain: ChainId,
    owner: Account,
}

impl<C> MemeMiner<C>
where
    C: ClientContext + 'static,
{
    pub async fn new(
        meme_proxy_application_id: ApplicationId,
        context: C,
        chain_listener_config: &mut ChainListenerConfig,
        default_chain: ChainId,
    ) -> Self {
        let chain = context
            .wallet()
            .get(default_chain)
            .await
            .expect("failed get default chain")
            .expect("invalid default chain");
        let owner = chain.owner.unwrap();

        // We don't need to process message
        chain_listener_config.skip_process_inbox = true;

        let storage = context.storage().clone();

        Self {
            context: Arc::new(Mutex::new(context)),
            storage,

            meme_proxy_application_id,

            new_block_notifier: Arc::new(Notify::new()),
            chain_listener_config: chain_listener_config.clone(),

            default_chain,
            owner: Account {
                chain_id: default_chain,
                owner,
            },
        }
    }

    async fn query_user_application<T>(
        &self,
        chain_id: ChainId,
        request: Request,
    ) -> Result<QueryOutcome<Response<T>>, MemeMinerError>
    where
        T: DeserializeOwned,
    {
        // We don't get chain id here to avoid recursive invocation
        let query = Query::user(
            self.meme_proxy_application_id.with_abi::<ProxyAbi>(),
            &request,
        )?;

        let client = self
            .context
            .lock()
            .await
            .make_chain_client(chain_id)
            .await?;

        let QueryOutcome {
            response,
            operations,
        } = client.query_application(query, None).await?;

        let QueryResponse::User(payload) = response else {
            unreachable!("cannot get a system response for a user query");
        };
        tracing::info!(
            "Query:\n\tchain {} \n\tapplication {} \n\trequest {:?}: \n\t{:?}",
            chain_id,
            self.meme_proxy_application_id,
            request,
            String::from_utf8(payload.clone()).expect("invalid response")
        );
        let response: Response<T> =
            serde_json::from_str(&String::from_utf8(payload).expect("invalid response"))?;

        Ok(QueryOutcome {
            response,
            operations,
        })
    }

    async fn meme_proxy_creator_chain_id(&self) -> Result<ChainId, MemeMinerError> {
        let request = Request::new(
            r#"
            query creatorChainId {
                creatorChainId
            }
            "#,
        );
        let outcome = self
            .query_user_application::<CreatorChainIdResponse>(self.default_chain, request)
            .await?;
        Ok(outcome.response.data.creator_chain_id)
    }

    async fn follow_proxy_chain(&self) -> Result<(), MemeMinerError> {
        let start_time = Instant::now();

        let meme_proxy_creator_chain_id = self.meme_proxy_creator_chain_id().await?;

        self.context
            .lock()
            .await
            .client()
            .track_chain(meme_proxy_creator_chain_id);
        let chain_client = self
            .context
            .lock()
            .await
            .make_chain_client(meme_proxy_creator_chain_id)
            .await?;
        chain_client
            .synchronize_chain_state(meme_proxy_creator_chain_id)
            .await?;
        self.context
            .lock()
            .await
            .update_wallet(&chain_client)
            .await?;

        tracing::info!(
            "Proxy chain followed and added in {} ms",
            start_time.elapsed().as_millis()
        );

        Ok(())
    }

    async fn miner_registered(&self) -> Result<bool, MemeMinerError> {
        let meme_proxy_creator_chain_id = self.meme_proxy_creator_chain_id().await?;

        let mut request = Request::new(
            r#"
            query minerRegistered($owner: String!) {
                minerRegistered(owner: $owner)
            }
            "#,
        );
        request = request.variables(Variables::from_json(serde_json::json!({
            "owner": self.owner.owner,
        })));

        let outcome = self
            .query_user_application::<MinerRegisteredResponse>(meme_proxy_creator_chain_id, request)
            .await?;
        Ok(outcome.response.data.miner_registered)
    }

    // Stole from node_service.rs
    async fn execute_operation<T>(
        &self,
        chain_id: ChainId,
        request: Request,
    ) -> Result<CryptoHash, MemeMinerError>
    where
        T: DeserializeOwned,
    {
        let QueryOutcome {
            response,
            operations,
        } = self.query_user_application::<T>(chain_id, request).await?;
        if operations.is_empty() {
            unreachable!("the query contains no operation");
        }

        let client = self
            .context
            .lock()
            .await
            .make_chain_client(chain_id)
            .await?;
        let hash = loop {
            let timeout = match client
                .execute_operations(operations.clone(), vec![])
                .await?
            {
                ClientOutcome::Committed(certificate) => break certificate.hash(),
                ClientOutcome::WaitForTimeout(timeout) => timeout,
            };
            let mut stream = client.subscribe()?;
            util::wait_for_next_round(&mut stream, timeout).await;
        };

        Ok(hash)
    }

    async fn register_miner(&self) -> Result<(), MemeMinerError> {
        let request = Request::new(
            r#"
            mutation registerMiner {
                registerMiner
            }
            "#,
        );
        let hash = self
            .execute_operation::<RegisterMinerResponse>(self.default_chain, request)
            .await?;
        tracing::info!("Hash {:?}", hash);
        Ok(())
    }

    pub fn meme_proxy_application_id(&self) -> ApplicationId {
        self.meme_proxy_application_id
    }

    async fn mine_task(&self, cancellation_token: CancellationToken) -> Result<(), MemeMinerError> {
        loop {
            tokio::select! {
                _ = self.new_block_notifier.notified() => {
                    // TODO: get new chains
                    // TODO: subscribe to block height and nonce
                    // TODO: assign new chains to owner
                    // TODO: if new block height or nonce got, stop previous mining and launch new one
                    // TODO: create Mine operation when hash got
                }
                _ = cancellation_token.cancelled() => {
                    tracing::info!("quit meme miner");
                    return Ok(());
                }
            }
        }
    }

    pub async fn run(&self, cancellation_token: CancellationToken) -> Result<(), MemeMinerError> {
        self.follow_proxy_chain().await?;

        let chain_listener = ChainListener::new(
            self.chain_listener_config.clone(),
            self.context.clone(),
            self.storage.clone(),
            cancellation_token.clone(),
            tokio::sync::mpsc::unbounded_channel().1,
        )
        .run(true)
        .await?;

        if !self.miner_registered().await? {
            self.register_miner().await?;
        }

        let mine_task = self.mine_task(cancellation_token);

        futures::select! {
            result = Box::pin(chain_listener).fuse() => result?,
            result = Box::pin(mine_task).fuse() => result?,
        };

        Ok(())
    }
}
