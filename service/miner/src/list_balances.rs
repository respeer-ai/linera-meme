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

    pub async fn exec(
        &self,
    ) -> Result<HashMap<ApplicationId, HashMap<Account, Amount>>, MemeMinerError> {
        let chains = self.proxy.meme_chains().await?;
        let mut balances = HashMap::default();

        // TODO: follow ams chain to get meme name

        for chain in chains {
            let Some(token) = chain.token else {
                continue;
            };

            let mut _balances: HashMap<Account, Amount> =
                balances.get(&token).unwrap_or(&HashMap::default()).clone();

            let meme = MemeApi::new(chain.clone(), Arc::clone(&self.wallet));
            let balance = meme.balance(None).await?;

            _balances.insert(meme.account(), balance);
            balances.insert(token, _balances);
        }

        Ok(balances)
    }
}

pub fn print_balances(balances: &HashMap<ApplicationId, HashMap<Account, Amount>>) {
    for (token, _balances) in balances {
        println!("\n=== Application: {} ===", token);

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
