use abi::swap::router::SwapOperation;
use async_graphql::{Error, Object};
use linera_base::{
    data_types::Amount,
    identifiers::{Account, ApplicationId, ChainId},
};

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
    async fn create_pool(
        &self,
        token_0_creator_chain_id: ChainId,
        token_0: ApplicationId,
        // User can also create meme-native pool for mining only meme
        token_1_creator_chain_id: Option<ChainId>,
        token_1: Option<ApplicationId>,
        amount_0: Amount,
        amount_1: Amount,
        to: Option<Account>,
    ) -> Result<Vec<u8>, Error> {
        Ok(bcs::to_bytes(&SwapOperation::CreatePool {
            token_0_creator_chain_id,
            token_0,
            token_1_creator_chain_id,
            token_1,
            amount_0,
            amount_1,
            to,
        })?)
    }
}
