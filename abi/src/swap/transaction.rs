use async_graphql::scalar;
use linera_sdk::linera_base_types::{Account, Amount, Timestamp};
use serde::{Deserialize, Serialize};

#[derive(Default, Debug, Deserialize, Serialize, Clone, Eq, PartialEq, Copy)]
pub enum TransactionType {
    #[default]
    BuyToken0,
    SellToken0,
    AddLiquidity,
    RemoveLiquidity,
}

scalar!(TransactionType);

#[derive(Debug, Clone, Deserialize, Serialize, Eq, PartialEq)]
#[serde(rename_all = "camelCase")]
pub struct Transaction {
    pub transaction_id: Option<u32>,
    pub transaction_type: TransactionType,
    pub from: Account,
    pub amount_0_in: Option<Amount>,
    pub amount_0_out: Option<Amount>,
    pub amount_1_in: Option<Amount>,
    pub amount_1_out: Option<Amount>,
    pub liquidity: Option<Amount>,
    pub created_at: Timestamp,
}

scalar!(Transaction);
