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

pub struct ListBalances<C>
where
    C: ClientContext,
{
    wallet: Arc<WalletApi<C>>,
    proxy: ProxyApi<C>,
}

#[derive(Tabled)]
struct Row {
    account: String,
    amount: String,
}

impl<C> ListBalances<C>
where
    C: ClientContext + 'static,
{
    pub async fn new(
        proxy_application_id: ApplicationId,
        context: C,
        default_chain: ChainId,
    ) -> Self {
        let context = Arc::new(Mutex::new(context));
        let wallet = Arc::new(WalletApi::new(Arc::clone(&context), default_chain).await);
        let proxy = ProxyApi::new(proxy_application_id, Arc::clone(&wallet));

        Self { wallet, proxy }
    }

    pub async fn exec(&self) -> Result<HashMap<String, HashMap<Account, Amount>>, MemeMinerError> {
        let chains = self.proxy.meme_chains().await?;
        let mut balances = HashMap::default();

        // TODO: sync proxy chain

        for chain in chains {
            let Some(token) = chain.token else {
                continue;
            };

            let meme = MemeApi::new(chain.clone(), Arc::clone(&self.wallet));
            let _meme = meme.meme().await?;

            // TODO: sync meme chain
            let redeemable_balance = meme.balance(None).await?;
            let redeemed_balance = meme.balance(Some(self.wallet.account())).await?;
            let creator_chain_id = self.wallet.application_creator_chain_id(token).await?;

            let key = format!("{}: {}:{}", _meme.ticker, creator_chain_id, token);
            let mut _balances: HashMap<Account, Amount> =
                balances.get(&key).unwrap_or(&HashMap::default()).clone();

            _balances.insert(meme.account(), redeemable_balance);
            _balances.insert(self.wallet.account(), redeemed_balance);
            balances.insert(key, _balances);
        }

        Ok(balances)
    }
}

pub fn print_balances(balances: &HashMap<String, HashMap<Account, Amount>>) {
    for (meme, _balances) in balances {
        println!("\n=== {} ===", meme);

        let rows: Vec<Row> = _balances
            .iter()
            .map(|(a, v)| Row {
                account: a.to_string(),
                amount: v.to_string(),
            })
            .collect();

        println!("{}", Table::new(rows));
    }
}
