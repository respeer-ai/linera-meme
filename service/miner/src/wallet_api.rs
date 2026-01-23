use std::{sync::Arc, time::Instant};

use async_graphql::Request;
use futures::lock::Mutex;
use linera_base::{
    crypto::CryptoHash,
    identifiers::{Account, AccountOwner, ApplicationId, ChainId},
};
use linera_client::chain_listener::ClientContext;
use linera_core::{data_types::ClientOutcome, Wallet};
use linera_execution::{Query, QueryOutcome, QueryResponse};
use linera_service::util;
use serde::{de::DeserializeOwned, Deserialize};

use crate::errors::MemeMinerError;

#[derive(Debug, Deserialize)]
struct CreatorChainIdResponse {
    #[serde(alias = "creatorChainId")]
    creator_chain_id: ChainId,
}

#[derive(Debug, Deserialize)]
pub struct Response<T> {
    pub data: T,
}

pub struct WalletApi<C>
where
    C: ClientContext,
{
    context: Arc<Mutex<C>>,

    default_chain: ChainId,
    owner: Account,
}

impl<C> WalletApi<C>
where
    C: ClientContext + 'static,
{
    pub async fn new(context: Arc<Mutex<C>>, default_chain: ChainId) -> Self {
        let chain = context
            .lock()
            .await
            .wallet()
            .get(default_chain)
            .await
            .expect("failed get default chain")
            .expect("invalid default chain");
        let owner = chain.owner.unwrap();

        Self {
            context,

            default_chain,
            owner: Account {
                chain_id: default_chain,
                owner,
            },
        }
    }

    pub async fn query_user_application<T>(
        &self,
        application_id: ApplicationId,
        chain_id: ChainId,
        request: Request,
    ) -> Result<QueryOutcome<Response<T>>, MemeMinerError>
    where
        T: DeserializeOwned,
    {
        // We don't get chain id here to avoid recursive invocation
        let query = Query::user_without_abi(application_id, &request)?;

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
            application_id,
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

    pub async fn application_creator_chain_id(
        &self,
        application_id: ApplicationId,
    ) -> Result<ChainId, MemeMinerError> {
        let request = Request::new(
            r#"
            query creatorChainId {
                creatorChainId
            }
            "#,
        );
        let outcome = self
            .query_user_application::<CreatorChainIdResponse>(
                application_id,
                self.default_chain,
                request,
            )
            .await?;
        Ok(outcome.response.data.creator_chain_id)
    }

    pub async fn follow_chain(&self, chain_id: ChainId) -> Result<(), MemeMinerError> {
        let start_time = Instant::now();

        let chain_client = self
            .context
            .lock()
            .await
            .make_chain_client(chain_id)
            .await?;
        chain_client.synchronize_chain_state(chain_id).await?;
        self.context
            .lock()
            .await
            .update_wallet(&chain_client)
            .await?;

        tracing::info!(
            "Chain followed and added in {} ms",
            start_time.elapsed().as_millis()
        );

        Ok(())
    }

    // Stole from node_service.rs
    pub async fn execute_operation<T>(
        &self,
        application_id: ApplicationId,
        chain_id: ChainId,
        request: Request,
    ) -> Result<CryptoHash, MemeMinerError>
    where
        T: DeserializeOwned,
    {
        tracing::info!("query application ...");
        let QueryOutcome {
            response: _,
            operations,
        } = self
            .query_user_application::<T>(application_id, chain_id, request)
            .await?;
        if operations.is_empty() {
            unreachable!("the query contains no operation");
        }

        let client = self
            .context
            .lock()
            .await
            .make_chain_client(chain_id)
            .await?;
        tracing::info!("execute operation ...");
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

    pub async fn initialize_chain(&self, chain_id: ChainId) -> Result<(), MemeMinerError> {
        let maybe_exist_chain = self
            .context
            .lock()
            .await
            .wallet()
            .get(chain_id)
            .await
            .expect("Failed get exists chain");
        match maybe_exist_chain {
            Some(_) => {}
            _ => self.follow_chain(chain_id).await?,
        }
        // We may fail here due to the meme chain is not assigned to us at the beginning
        // So we should retry due to listener will sync chain in background

        self.context
            .lock()
            .await
            .assign_new_chain_to_key(chain_id, self.owner.owner)
            .await?;

        Ok(())
    }

    pub fn default_chain(&self) -> ChainId {
        self.default_chain
    }

    pub fn owner(&self) -> AccountOwner {
        self.owner.owner
    }
}
