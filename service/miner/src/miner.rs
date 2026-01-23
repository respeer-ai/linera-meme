use std::{cmp::Ordering, collections::HashMap, str::FromStr, sync::Arc, time::Instant};

use abi::{
    hash::{hash_cmp, hash_increment},
    meme::{MemeAbi, MiningBase, MiningInfo},
    proxy::{Chain, Miner, ProxyAbi},
};
use async_graphql::{Request, Value, Variables};
use futures::{lock::Mutex, FutureExt as _};
use linera_base::{
    crypto::CryptoHash,
    data_types::{Amount, BlockHeight},
    identifiers::{Account, AccountOwner, ApplicationId, ChainId},
};
use linera_client::chain_listener::{ChainListener, ChainListenerConfig, ClientContext};
use linera_core::{data_types::ClientOutcome, Wallet};
use linera_execution::{Query, QueryOutcome, QueryResponse};
use linera_service::util;
use serde::{de::DeserializeOwned, Deserialize};
use tokio::{
    sync::Notify,
    task::JoinHandle,
    time::{sleep, Duration},
};
use tokio_util::sync::CancellationToken;

use crate::errors::MemeMinerError;

#[derive(Debug, Deserialize)]
struct CreatorChainIdResponse {
    #[serde(alias = "creatorChainId")]
    creator_chain_id: ChainId,
}

#[derive(Debug, Deserialize)]
struct MinerResponse {
    #[serde(alias = "miner")]
    miner: Option<Miner>,
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
struct MineResponse {
    mine: Vec<u8>,
}

#[derive(Debug, Deserialize)]
struct MemeChainsResponse {
    #[serde(alias = "memeChains")]
    meme_chains: Vec<Chain>,
}

#[derive(Debug, Deserialize)]
struct MiningInfoResponse {
    #[serde(alias = "miningInfo")]
    mining_info: Option<MiningInfo>,
}

#[derive(Debug, Deserialize)]
struct BalanceOfResponse {
    #[serde(alias = "balanceOf")]
    balance_of: Amount,
}

#[derive(Debug, Deserialize)]
struct Response<T> {
    data: T,
}

#[derive(Debug, Clone)]
struct MiningChain {
    chain: Chain,
    new_block_notifier: Arc<Notify>,
    mining_info: Option<MiningInfo>,
    nonce: Option<CryptoHash>,
    mined_height: Option<BlockHeight>,
}

pub struct MemeMiner<C>
where
    C: ClientContext,
{
    context: Arc<Mutex<C>>,
    storage: <C::Environment as linera_core::Environment>::Storage,

    proxy_application_id: ApplicationId,

    new_block_notifier: Arc<Notify>,
    pub chain_listener_config: ChainListenerConfig,

    default_chain: ChainId,
    owner: Account,

    mining_chains: Mutex<HashMap<ChainId, MiningChain>>,
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

            proxy_application_id,

            new_block_notifier: Arc::new(Notify::new()),
            chain_listener_config: chain_listener_config.clone(),

            default_chain,
            owner: Account {
                chain_id: default_chain,
                owner,
            },

            mining_chains: Mutex::new(HashMap::default()),
        }
    }

    async fn query_user_application<T>(
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

    async fn application_creator_chain_id(
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

    async fn proxy_creator_chain_id(&self) -> Result<ChainId, MemeMinerError> {
        self.application_creator_chain_id(self.proxy_application_id)
            .await
    }

    async fn follow_chain(&self, chain_id: ChainId) -> Result<(), MemeMinerError> {
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

    async fn follow_proxy_chain(&self) -> Result<(), MemeMinerError> {
        let proxy_creator_chain_id = self.proxy_creator_chain_id().await?;
        self.follow_chain(proxy_creator_chain_id).await
    }

    async fn miner_registered(&self) -> Result<bool, MemeMinerError> {
        let proxy_creator_chain_id = self.proxy_creator_chain_id().await?;

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
            .query_user_application::<MinerRegisteredResponse>(
                self.proxy_application_id,
                proxy_creator_chain_id,
                request,
            )
            .await?;
        Ok(outcome.response.data.miner_registered)
    }

    async fn miner(&self) -> Result<Option<Miner>, MemeMinerError> {
        let proxy_creator_chain_id = self.proxy_creator_chain_id().await?;

        let mut request = Request::new(
            r#"
            query miner($owner: String!) {
                miner(owner: $owner) {
                    owner
                    registeredAt
                }
            }
            "#,
        );
        request = request.variables(Variables::from_json(serde_json::json!({
            "owner": self.owner.owner,
        })));

        let outcome = self
            .query_user_application::<MinerResponse>(
                self.proxy_application_id,
                proxy_creator_chain_id,
                request,
            )
            .await?;
        Ok(outcome.response.data.miner)
    }

    // Stole from node_service.rs
    async fn execute_operation<T>(
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
            response,
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

    async fn register_miner(&self) -> Result<(), MemeMinerError> {
        let request = Request::new(
            r#"
            mutation registerMiner {
                registerMiner
            }
            "#,
        );
        let hash = self
            .execute_operation::<RegisterMinerResponse>(
                self.proxy_application_id,
                self.default_chain,
                request,
            )
            .await?;
        tracing::info!("Hash {:?}", hash);
        Ok(())
    }

    async fn mine(&self, chain: Chain, nonce: CryptoHash) -> Result<(), MemeMinerError> {
        // TODO: also process maker deal here
        let mut request = Request::new(
            r#"
            mutation mine($nonce: CryptoHash!) {
                mine(nonce: $nonce)
            }
            "#,
        );

        request = request.variables(Variables::from_json(serde_json::json!({
            "nonce": nonce,
        })));
        let hash = self
            .execute_operation::<MineResponse>(chain.token.unwrap(), chain.chain_id, request)
            .await?;
        tracing::info!("Hash {:?}", hash);
        Ok(())
    }

    async fn balance(&self, chain: &Chain) -> Result<Amount, MemeMinerError> {
        // Mining reward is on meme chain, user need to redeem to their own chain
        let account = Account {
            chain_id: chain.chain_id,
            owner: self.owner.owner,
        };
        let mut request = Request::new(
            r#"
            query balanceOf($owner: String!) {
                balanceOf(owner: $owner)
            }
            "#,
        );

        request = request.variables(Variables::from_json(serde_json::json!({
            "owner": account.to_string(),
        })));

        let outcome = self
            .query_user_application::<BalanceOfResponse>(
                chain.token.unwrap(),
                chain.chain_id,
                request,
            )
            .await?;
        Ok(outcome.response.data.balance_of)
    }

    pub fn proxy_application_id(&self) -> ApplicationId {
        self.proxy_application_id
    }

    async fn meme_chains(&self) -> Result<Vec<Chain>, MemeMinerError> {
        let Some(miner) = self.miner().await? else {
            // Miner is already registered so we just wait here
            tracing::warn!("miner is not registered, wait for next round");
            return Ok(Vec::new());
        };

        let proxy_creator_chain_id = self.proxy_creator_chain_id().await?;

        let mut request = Request::new(
            r#"
            query memeChains($createdAfter: Timestamp) {
                memeChains(createdAfter: $createdAfter) {
                    chainId
                    createdAt
                    token
                }
            }
            "#,
        );

        request = request.variables(Variables::from_json(serde_json::json!({
            // Every miner can mine every meme chain right now
            "createdAfter": 0,
        })));

        let outcome = self
            .query_user_application::<MemeChainsResponse>(
                self.proxy_application_id,
                proxy_creator_chain_id,
                request,
            )
            .await?;
        Ok(outcome.response.data.meme_chains)
    }

    async fn mining_info(&self, chain: &Chain) -> Result<Option<MiningInfo>, MemeMinerError> {
        let mut request = Request::new(
            r#"
            query miningInfo {
                miningInfo {
                    initialTarget
                    target
                    newTarget
                    blockDuration
                    targetBlockDuration
                    targetAdjustmentBlocks
                    emptyBlockRewardPercent
                    initialRewardAmount
                    halvingCycle
                    nextHalvingAt
                    rewardAmount
                    miningHeight
                    miningExecutions
                    previousNonce
                }
            }
            "#,
        );

        let outcome = self
            .query_user_application::<MiningInfoResponse>(
                chain.token.unwrap(),
                chain.chain_id,
                request,
            )
            .await?;
        Ok(outcome.response.data.mining_info)
    }

    fn try_one_batch(&self, chain: &MiningChain, nonce: CryptoHash) -> Option<CryptoHash> {
        let mining_info = chain.mining_info.as_ref().unwrap();

        let mining_base = MiningBase {
            height: mining_info.mining_height,
            nonce,
            chain_id: chain.chain.chain_id,
            signer: self.owner.owner,
            previous_nonce: mining_info.previous_nonce,
        };

        let hash = CryptoHash::new(&mining_base);

        let result = match hash_cmp(hash, mining_info.target) {
            Ordering::Less => Some(hash),
            Ordering::Equal => Some(hash),
            Ordering::Greater => None,
        };

        if result.is_some() {
            tracing::info!(?chain.chain.chain_id, ?mining_base, ?nonce, ?hash, "mined");
        }

        result
    }

    async fn mine_chain(
        &self,
        chain: &mut MiningChain,
        cancellation_token: CancellationToken,
    ) -> Result<(), MemeMinerError> {
        if chain.chain.token.is_some() {
            chain.mining_info = self.mining_info(&chain.chain).await?;
            if chain.mining_info.is_some() {
                chain.nonce = Some(chain.mining_info.as_ref().unwrap().previous_nonce);
            }
        }

        let mut start_time = Instant::now();

        loop {
            tokio::select! {
                _ = chain.new_block_notifier.notified() => {
                    if chain.chain.token.is_none() {
                        continue;
                    }
                    chain.mining_info = self.mining_info(&chain.chain).await?;
                    if chain.mining_info.is_none() {
                        return Ok(());
                    }
                    chain.nonce = Some(chain.mining_info.as_ref().unwrap().previous_nonce);

                    let balance = self.balance(&chain.chain).await;

                    tracing::info!(
                        ?chain.chain.chain_id,
                        mining_info=?chain.mining_info.as_ref().unwrap(),
                        nonce=?chain.nonce.unwrap(),
                        ?balance,
                        "new mining info",
                    );

                    start_time = Instant::now();
                }
                _ = cancellation_token.cancelled() => {
                    tracing::info!(?chain.chain.chain_id, "quit chain task");
                    return Ok(());
                }
                _ = tokio::task::yield_now(),
                if chain.chain.token.is_some()
                    && chain.mining_info.is_some()
                        && (chain.mined_height.is_none() || chain.mined_height.unwrap() < chain.mining_info.as_ref().unwrap().mining_height)
                        && chain.nonce.is_some() => {
                    let nonce = chain.nonce.unwrap();
                    let mining_info = chain.mining_info.as_ref().unwrap();

                    // We only mine one batch (for cpu is one hash, for GPU is one batch calculation)
                    let Some(hash) = self.try_one_batch(chain, nonce) else {
                        chain.nonce = Some(hash_increment(nonce));
                        continue;
                    };

                    let elapsed = start_time.elapsed().as_millis();
                    tracing::info!(
                        ?chain.chain.chain_id,
                        ?mining_info,
                        ?hash,
                        ?elapsed,
                        ?nonce,
                        "calculated one hash",
                    );

                    let mut submit_time = Instant::now();
                    match self.mine(chain.chain.clone(), nonce).await {
                        Ok(_) => {
                            chain.mined_height = Some(mining_info.mining_height);
                        },
                        Err(err) => tracing::warn!(error=?err, "failed mine"),
                    }
                    let elapsed = submit_time.elapsed().as_millis();
                    tracing::info!("took {} ms to submit", elapsed);
                }
                _ = sleep(Duration::from_secs(1)),
                if chain.chain.token.is_none()
                    || chain.mining_info.is_none()
                        || chain.mined_height.is_none()
                        || chain.mined_height.unwrap() >= chain.mining_info.as_ref().unwrap().mining_height
                        || chain.nonce.is_none() => {
                    chain.new_block_notifier.notify_one();
                    tracing::info!(?chain.chain.chain_id, "waiting for new block");
                }
            }
        }

        Ok(())
    }

    async fn handle_chain(
        &self,
        chain: Chain,
        cancellation_token: CancellationToken,
    ) -> Result<Option<MiningChain>, MemeMinerError> {
        let mut guard = self.mining_chains.lock().await;

        if guard.contains_key(&chain.chain_id) {
            return Ok(None);
        }

        let maybe_exist_chain = self
            .context
            .lock()
            .await
            .wallet()
            .get(chain.chain_id)
            .await
            .expect("Failed get exists chain");
        match maybe_exist_chain {
            Some(_) => {}
            _ => self.follow_chain(chain.chain_id).await?,
        }
        // We may fail here due to the meme chain is not assigned to us at the beginning
        // So we should retry due to listener will sync chain in background

        self.context
            .lock()
            .await
            .assign_new_chain_to_key(chain.chain_id, self.owner.owner)
            .await?;

        // TODO: do we need to listen it in ChainListener here (run_with_chain_id) ?
        // ChainListener will provide subscription to new chain block, then we can get height and nonce there

        let mining_chain = MiningChain {
            chain: chain.clone(),
            new_block_notifier: Arc::new(Notify::new()),
            mining_info: None,
            nonce: None,
            mined_height: None,
        };

        guard.insert(chain.chain_id, mining_chain.clone());

        Ok(Some(mining_chain))
    }

    async fn mine_task(
        self: Arc<Self>,
        cancellation_token: CancellationToken,
    ) -> Result<(), MemeMinerError> {
        loop {
            tokio::select! {
                _ = self.new_block_notifier.notified() => {
                    let chains = self.meme_chains().await?;

                    for chain in chains {
                        let mining_chain = match self.handle_chain(chain.clone(), cancellation_token.clone()).await {
                            Ok(Some(mining_chain)) => mining_chain,
                            _ => continue,
                        };

                        let _cancellation_token = cancellation_token.clone();
                        let miner = Arc::clone(&self);
                        let mut mining_chain = mining_chain;

                        tokio::spawn(async move {
                            if let Err(err) = miner.mine_chain(&mut mining_chain.clone(), _cancellation_token).await {
                                tracing::error!(?chain.chain_id, error = ?err, "mine chain failed");
                            }

                            let mut guard = miner.mining_chains.lock().await;
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
                    let mut guard = miner.mining_chains.lock().await;
                    if let Some(entry) = guard.get(&chain_id) {
                        entry.new_block_notifier.notify_one();
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
