use abi::{
    meme::{InstantiationArgument as MemeInstantiationArgument, MemeParameters},
    proxy::ProxyOperation,
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
    async fn create_meme(
        &self,
        meme_instantiation_argument: MemeInstantiationArgument,
        meme_parameters: MemeParameters,
    ) -> Result<Vec<u8>, Error> {
        Ok(bcs::to_bytes(&ProxyOperation::CreateMeme {
            meme_instantiation_argument,
            meme_parameters,
        })?)
    }
}
