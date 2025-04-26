use async_graphql::SimpleObject;
use linera_sdk::{
    linera_base_types::{Account, Amount, Timestamp},
    views::{linera_views, QueueView, RootView, ViewStorageContext},
};

use deposit::Deposit;

#[derive(RootView, SimpleObject)]
#[view(context = "ViewStorageContext")]
pub struct DepositState {
    pub deposits: QueueView<Deposit>,
}

#[allow(dead_code)]
impl DepositState {
    pub(crate) fn deposit(&mut self, to: Account, amount: Amount, timestamp: Timestamp) {
        self.deposits.push_back(Deposit {
            to,
            amount,
            created_at: timestamp,
        });
    }
}
