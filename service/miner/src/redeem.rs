use std::sync::Arc;

use futures::lock::Mutex;
use linera_base::{
    data_types::Amount,
    identifiers::{ApplicationId, ChainId},
};
use linera_client::chain_listener::ClientContext;

use crate::{
    errors::MemeMinerError, meme_api::MemeApi, proxy_api::ProxyApi, wallet_api::WalletApi,
};

pub struct Redeem<C>
where
    C: ClientContext,
{
    wallet: Arc<WalletApi<C>>,
    proxy: ProxyApi<C>,
    token: ApplicationId,
    amount: Option<Amount>,
}

impl<C> Redeem<C>
where
    C: ClientContext + 'static,
{
    pub async fn new(
        proxy_application_id: ApplicationId,
        context: C,
        default_chain: ChainId,
        token: ApplicationId,
        amount: Option<Amount>,
    ) -> Self {
        let context = Arc::new(Mutex::new(context));
        let wallet = Arc::new(WalletApi::new(Arc::clone(&context), default_chain).await);
        let proxy = ProxyApi::new(proxy_application_id, Arc::clone(&wallet));

        Self {
            wallet,
            proxy,
            token,
            amount,
        }
    }

    pub async fn exec(&self) -> Result<(), MemeMinerError> {
        self.proxy.follow_chain().await?;

        let Some(chain) = self.proxy.meme_chain(self.token).await? else {
            tracing::warn!(?self.token, "not ready");
            return Ok(());
        };

        if chain.token.is_none() {
            tracing::warn!(?self.token, "not ready");
            return Ok(());
        };

        let meme = MemeApi::new(chain.clone(), Arc::clone(&self.wallet));
        let _meme = meme.meme().await?;

        meme.follow_chain().await?;

        let redeemable_balance = meme.balance(None).await?;
        if redeemable_balance < self.amount.unwrap_or(Amount::ZERO) {
            tracing::error!(?self.token, ?redeemable_balance, ?self.amount, "insufficient balance");
            return Ok(());
        }

        meme.redeem(self.amount).await?;
        let redeemed_balance = meme.balance(Some(self.wallet.account())).await?;
        tracing::info!(?self.token, ?redeemed_balance, "redeemed");

        Ok(())
    }
}
