use async_graphql::SimpleObject;
use linera_sdk::linera_base_types::{Account, Amount, Timestamp};
use serde::{Deserialize, Serialize};
use thiserror::Error;

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize, SimpleObject)]
pub struct Deposit {
    pub to: Account,
    pub amount: Amount,
    pub created_at: Timestamp,
}

#[derive(Debug, Error)]
#[allow(dead_code)]
pub enum DepositError {}
