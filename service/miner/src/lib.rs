mod command;
mod errors;
mod options;

use std::{str::FromStr, sync::Arc};

use abi::proxy::ProxyAbi;
use async_graphql::Request;
use errors::MemeMinerError;
use futures::{lock::Mutex, FutureExt as _};
use linera_base::identifiers::{Account, ApplicationId, ChainId};
use linera_client::chain_listener::{ChainListener, ChainListenerConfig, ClientContext};
use linera_core::Wallet;
use linera_execution::Query;
use tokio::sync::Notify;
use tokio_util::sync::CancellationToken;

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

    async fn _meme_proxy_creator_chain_id(&self) -> Result<ChainId, MemeMinerError> {
        let client = self
            .context
            .lock()
            .await
            .make_chain_client(self.default_chain)
            .await?;

        let query = Request::new("{ creatorChainId }");
        let query = Query::user(
            self.meme_proxy_application_id.with_abi::<ProxyAbi>(),
            &query,
        )?;
        let outcome = client.query_application(query, None).await?;

        tracing::info!("{:?}", outcome);

        Err(MemeMinerError::NotImplemented)
    }

    fn check_miner(&self) -> bool {
        false
    }

    fn register_miner(&self) {}

    pub fn meme_proxy_application_id(&self) -> ApplicationId {
        self.meme_proxy_application_id
    }

    async fn mine_task(&self, cancellation_token: CancellationToken) {
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
                    break;
                }
            }
        }
    }

    pub async fn run(&self, cancellation_token: CancellationToken) -> anyhow::Result<()> {
        // TODO: sync chain
        // TODO: get meme proxy creator chain id
        // TODO: check if chain is miner, if not, register with default chain (cli.query_user_application)
        if !self.check_miner() {
            self.register_miner();
        }

        let chain_listener = ChainListener::new(
            self.chain_listener_config.clone(),
            self.context.clone(),
            self.storage.clone(),
            cancellation_token.clone(),
            tokio::sync::mpsc::unbounded_channel().1,
        )
        .run(false)
        .await?;
        let mine_task = self.mine_task(cancellation_token);

        futures::select! {
            result = Box::pin(chain_listener).fuse() => result?,
            _ = Box::pin(mine_task).fuse() => {},
        };

        Ok(())
    }
}
