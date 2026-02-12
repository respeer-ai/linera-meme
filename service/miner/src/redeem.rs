use std::{collections::HashMap, sync::Arc};

use futures::lock::Mutex;
use linera_base::{
    data_types::Amount,
    identifiers::{Account, ApplicationId, ChainId},
};
use linera_client::chain_listener::ClientContext;
use tabled::{Table, Tabled};

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
    amount: Amount,
}

#[derive(Tabled)]
struct Row {
    account: String,
    amount: String,
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
        amount: Amount,
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
        let chain = self.proxy.meme_chain(self.token).await?;
        let Some(token) = chain.token else {
            tracing::warn!(?self.token, "not ready");
            return;
        };

        let meme = MemeApi::new(chain.clone(), Arc::clone(&self.wallet));
        let _meme = meme.meme().await?;

        let redeemable_balance = meme.balance(None).await?;
        if balance < self.amount {
            tracing::error!(?self.token, ?redeemable_balance, ?self.amount, "insufficient balance");
            return;
        }

        meme.redeem(self.amount).await?;
        let redeemed_balance = meme.balance(Some(self.wallet.account())).await?;
        tracing::info!(?self.token, ?redeemed_balance, "redeemed");

        Ok(())
    }
}
