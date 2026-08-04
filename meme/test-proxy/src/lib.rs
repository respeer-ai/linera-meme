use abi::meme::InitializeArgument;
use async_graphql::{Request, Response};
use linera_sdk::linera_base_types::{ApplicationId, ContractAbi, ServiceAbi};
use serde::{Deserialize, Serialize};

pub struct FakeProxyAbi;

impl ContractAbi for FakeProxyAbi {
    type Operation = FakeProxyOperation;
    type Response = FakeProxyResponse;
}

impl ServiceAbi for FakeProxyAbi {
    type Query = Request;
    type QueryResponse = Response;
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub enum FakeProxyOperation {
    InitializeMeme {
        meme_app_id: ApplicationId,
        argument: InitializeArgument,
    },
}

#[derive(Debug, Clone, Deserialize, Serialize, Default)]
pub enum FakeProxyResponse {
    #[default]
    Ok,
    Fail(String),
}
