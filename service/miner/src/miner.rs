use std::{collections::HashMap, sync::Arc};

use futures::{lock::Mutex, FutureExt as _};
use linera_base::identifiers::{ApplicationId, ChainId};
use linera_client::chain_listener::{ChainListener, ChainListenerConfig, ClientContext};
use tokio::{
    sync::Notify,
    time::{sleep, Duration},
};
use tokio_util::sync::CancellationToken;

use crate::{
    chain_miner::ChainMiner, errors::MemeMinerError, proxy_api::ProxyApi, wallet_api::WalletApi,
};

pub struct MemeMiner<C>
where
    C: ClientContext,
{
    context: Arc<Mutex<C>>,
    storage: <C::Environment as linera_core::Environment>::Storage,

    wallet: Arc<WalletApi<C>>,
    proxy: ProxyApi<C>,
    miners: Mutex<HashMap<ChainId, Arc<ChainMiner<C>>>>,

    new_block_notifier: Arc<Notify>,
    pub chain_listener_config: ChainListenerConfig,
}

impl<C> MemeMiner<C>
where
    C: ClientContext + 'static,
{
    pub async fn new(
        proxy_application_id: ApplicationId,
        context: C,
        chain_listener_config: &mut ChainListenerConfig,
        default_chain: ChainId,
    ) -> Self {
        let storage = context.storage().clone();

        let context = Arc::new(Mutex::new(context));
        let wallet = Arc::new(WalletApi::new(Arc::clone(&context), default_chain).await);
        let proxy = ProxyApi::new(proxy_application_id, Arc::clone(&wallet));

        // We don't need to process message
        chain_listener_config.skip_process_inbox = true;

        Self {
            context,
            storage,
            wallet,
            proxy,
            miners: Mutex::new(HashMap::default()),
            new_block_notifier: Arc::new(Notify::new()),
            chain_listener_config: chain_listener_config.clone(),
        }
    }

    async fn proxy_creator_chain_id(&self) -> Result<ChainId, MemeMinerError> {
        self.proxy.creator_chain_id().await
    }

    async fn follow_proxy_chain(&self) -> Result<(), MemeMinerError> {
        self.proxy.follow_chain().await
    }

    async fn miner_registered(&self) -> Result<bool, MemeMinerError> {
        self.proxy.miner_registered().await
    }

    async fn register_miner(&self) -> Result<(), MemeMinerError> {
        self.proxy.register_miner().await
    }

    pub fn proxy_application_id(&self) -> ApplicationId {
        self.proxy.application_id()
    }

    async fn mine_task(
        self: Arc<Self>,
        cancellation_token: CancellationToken,
    ) -> Result<(), MemeMinerError> {
        loop {
            tokio::select! {
                _ = self.new_block_notifier.notified() => {
                    let chains = self.proxy.meme_chains().await?;

                    for chain in chains {
                        let mut guard = self.miners.lock().await;
                        if guard.contains_key(&chain.chain_id) {
                            continue;
                        }

                        self.wallet.initialize_chain(chain.chain_id).await?;

                        let chain_miner = Arc::new(ChainMiner::new(chain.clone(), Arc::clone(&self.wallet)).await);
                        guard.insert(chain.chain_id, Arc::clone(&chain_miner));

                        let _cancellation_token = cancellation_token.clone();
                        let miner = Arc::clone(&self);

                        tokio::spawn(async move {
                            let mut chain_miner = Arc::try_unwrap(chain_miner).unwrap_or_else(|_| panic!("only one strong ref allowed"));

                            if let Err(err) = chain_miner.run(_cancellation_token).await {
                                tracing::error!(?chain.chain_id, error = ?err, "mine chain failed");
                            }

                            let mut guard = miner.miners.lock().await;
                            guard.remove(&chain.chain_id);
                        });

                    }
                }
                _ = sleep(Duration::from_secs(30)) => {
                    self.new_block_notifier.notify_one();
                }
                _ = cancellation_token.cancelled() => {
                    tracing::info!("quit meme miner");
                    return Ok(());
                }
            }
        }
    }

    pub async fn run(
        self: Arc<Self>,
        cancellation_token: CancellationToken,
    ) -> Result<(), MemeMinerError> {
        self.follow_proxy_chain().await?;

        let chain_listener = ChainListener::new(
            self.chain_listener_config.clone(),
            self.context.clone(),
            self.storage.clone(),
            cancellation_token.clone(),
            Arc::new(Mutex::new(tokio::sync::mpsc::unbounded_channel().1)),
            true,
        );

        let mut receiver = chain_listener.subscribe_new_block();
        let notifier = self.new_block_notifier.clone();
        let proxy_creator_chain_id = self.proxy_creator_chain_id().await?;
        let miner = Arc::clone(&self);

        tokio::spawn(async move {
            while let Ok(chain_id) = receiver.recv().await {
                tracing::info!("new block of chain {}", chain_id);
                if chain_id == proxy_creator_chain_id {
                    notifier.notify_one();
                } else {
                    let guard = miner.miners.lock().await;
                    if let Some(entry) = guard.get(&chain_id) {
                        entry.notify();
                    } else {
                        tracing::warn!(?chain_id, "no mining chain");
                    }
                }
            }
        });

        let chain_listener = chain_listener.run().await?;

        if !self.miner_registered().await? {
            self.register_miner().await?;
        }

        let notifier = self.new_block_notifier.clone();
        notifier.notify_one();
        let mine_task = self.mine_task(cancellation_token);

        futures::select! {
            result = Box::pin(chain_listener).fuse() => result?,
            result = Box::pin(mine_task).fuse() => result?,
        };

        Ok(())
    }
}
