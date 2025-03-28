use abi::swap::pool::PoolOperation;
use linera_base::{
    data_types::{Amount, Timestamp},
    identifiers::Account,
};
use async_graphql::{Error, Object};

pub struct QueryRoot;

#[Object]
impl QueryRoot {
    async fn parse_query(&self) -> u64 {
        0
    }
}

pub struct MutationRoot;

#[Object]
impl MutationRoot {
    // TODO: do we need to return human readable operation, too ?
    async fn swap(
        &self,
        amount_0_in: Option<Amount>,
        amount_1_in: Option<Amount>,
        amount_0_out_min: Option<Amount>,
        amount_1_out_min: Option<Amount>,
        to: Option<Account>,
        block_timestamp: Option<Timestamp>
    ) -> Result<Vec<u8>, Error> {
        Ok(bcs::to_bytes(&PoolOperation::Swap {
            amount_0_in,
            amount_1_in,
            amount_0_out_min,
            amount_1_out_min,
            to,
            block_timestamp
        })?)
    }
}
