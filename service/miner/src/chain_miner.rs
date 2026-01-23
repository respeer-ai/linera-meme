use std::{cmp::Ordering, sync::Arc, time::Instant};

use abi::{
    hash::{hash_cmp, hash_increment},
    meme::{MiningBase, MiningInfo},
    proxy::Chain,
};
use linera_base::{
    crypto::CryptoHash,
    data_types::{Amount, BlockHeight},
};
use linera_client::chain_listener::ClientContext;
use tokio::{
    sync::Notify,
    time::{sleep, Duration},
};
use tokio_util::sync::CancellationToken;

use crate::{errors::MemeMinerError, meme_api::MemeApi, wallet_api::WalletApi};

pub struct ChainMiner<C>
where
    C: ClientContext,
{
    wallet: Arc<WalletApi<C>>,

    meme: MemeApi<C>,
    chain: Chain,

    new_block_notifier: Arc<Notify>,

    mining_info: Option<MiningInfo>,
    nonce: Option<CryptoHash>,
    mined_height: Option<BlockHeight>,
}

impl<C> ChainMiner<C>
where
    C: ClientContext + 'static,
{
    pub async fn new(chain: Chain, wallet: Arc<WalletApi<C>>) -> Self {
        let meme = MemeApi::new(chain.clone(), Arc::clone(&wallet));

        Self {
            wallet,
            meme,
            chain,
            new_block_notifier: Arc::new(Notify::new()),
            mining_info: None,
            nonce: None,
            mined_height: None,
        }
    }

    async fn mine(&self, nonce: CryptoHash) -> Result<(), MemeMinerError> {
        // TODO: also process maker deal here
        self.meme.mine(nonce).await
    }

    async fn balance(&self) -> Result<Amount, MemeMinerError> {
        self.meme.balance().await
    }

    async fn mining_info(&self) -> Result<Option<MiningInfo>, MemeMinerError> {
        self.meme.mining_info().await
    }

    fn try_one_batch(&self, nonce: CryptoHash) -> Option<CryptoHash> {
        let mining_info = self.mining_info.as_ref().unwrap();

        let mining_base = MiningBase {
            height: mining_info.mining_height,
            nonce,
            chain_id: self.chain.chain_id,
            signer: self.wallet.owner(),
            previous_nonce: mining_info.previous_nonce,
        };

        let hash = CryptoHash::new(&mining_base);

        let result = match hash_cmp(hash, mining_info.target) {
            Ordering::Less => Some(hash),
            Ordering::Equal => Some(hash),
            Ordering::Greater => None,
        };

        if result.is_some() {
            tracing::info!(?self.chain.chain_id, ?mining_base, ?nonce, ?hash, "mined");
        }

        result
    }

    pub async fn run(
        &mut self,
        cancellation_token: CancellationToken,
    ) -> Result<(), MemeMinerError> {
        if self.chain.token.is_some() {
            self.mining_info = self.mining_info().await?;
            if self.mining_info.is_some() {
                self.nonce = Some(self.mining_info.as_ref().unwrap().previous_nonce);
            }
        }

        let mut start_time = Instant::now();

        loop {
            tokio::select! {
                _ = self.new_block_notifier.notified() => {
                    if self.chain.token.is_none() {
                        continue;
                    }
                    self.mining_info = self.mining_info().await?;
                    if self.mining_info.is_none() {
                        return Ok(());
                    }
                    self.nonce = Some(self.mining_info.as_ref().unwrap().previous_nonce);

                    let balance = self.balance().await;

                    tracing::info!(
                        ?self.chain.chain_id,
                        mining_info=?self.mining_info.as_ref().unwrap(),
                        nonce=?self.nonce.unwrap(),
                        ?balance,
                        "new mining info",
                    );

                    start_time = Instant::now();
                }
                _ = cancellation_token.cancelled() => {
                    tracing::info!(?self.chain.chain_id, "quit chain miner");
                    return Ok(());
                }
                _ = tokio::task::yield_now(),
                if self.chain.token.is_some()
                    && self.mining_info.is_some()
                        && (self.mined_height.is_none() || self.mined_height.unwrap() < self.mining_info.as_ref().unwrap().mining_height)
                        && self.nonce.is_some() => {
                    let nonce = self.nonce.unwrap();
                    let mining_info = self.mining_info.as_ref().unwrap();

                    // We only mine one batch (for cpu is one hash, for GPU is one batch calculation)
                    let Some(hash) = self.try_one_batch(nonce) else {
                        self.nonce = Some(hash_increment(nonce));
                        continue;
                    };

                    let elapsed = start_time.elapsed().as_millis();
                    tracing::info!(
                        ?self.chain.chain_id,
                        ?mining_info,
                        ?hash,
                        ?elapsed,
                        ?nonce,
                        "calculated one hash",
                    );

                    let submit_time = Instant::now();
                    match self.mine(nonce).await {
                        Ok(_) => {
                            self.mined_height = Some(mining_info.mining_height);
                        },
                        Err(err) => tracing::warn!(error=?err, "failed mine"),
                    }
                    let elapsed = submit_time.elapsed().as_millis();
                    tracing::info!("took {} ms to submit", elapsed);
                }
                _ = sleep(Duration::from_secs(1)),
                if self.chain.token.is_none()
                    || self.mining_info.is_none()
                        || self.mined_height.is_none()
                        || self.mined_height.unwrap() >= self.mining_info.as_ref().unwrap().mining_height
                        || self.nonce.is_none() => {
                    self.new_block_notifier.notify_one();
                    tracing::info!(?self.chain.chain_id, "waiting for new block");
                }
            }
        }
    }

    pub fn notify(&self) {
        self.new_block_notifier.notify_one()
    }
}
