use async_graphql::{scalar, InputObject, Request, Response};
use linera_sdk::{
    graphql::GraphQLMutationRoot,
    linera_base_types::{Amount, ApplicationId, ContractAbi, ServiceAbi},
};
use serde::{Deserialize, Serialize};

pub struct PoolAbi;

impl ContractAbi for PoolAbi {
    type Operation = PoolOperation;
    type Response = PoolResponse;
}

impl ServiceAbi for PoolAbi {
    type Query = Request;
    type QueryResponse = Response;
}

#[derive(Debug, Deserialize, Serialize, GraphQLMutationRoot)]
pub enum PoolOperation {
    Approved { token: ApplicationId },
    Rejected { token: ApplicationId },
}

#[derive(Debug, Deserialize, Serialize, Default)]
pub enum PoolResponse {
    #[default]
    Ok,
}

#[derive(Clone, Copy, Debug, Deserialize, Serialize)]
pub struct PoolParameters {
    pub token_0: ApplicationId,
    pub token_1: Option<ApplicationId>,
    pub router_application_id: ApplicationId,
}

scalar!(PoolParameters);

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize, InputObject)]
pub struct InstantiationArgument {
    pub amount_0: Amount,
    pub amount_1: Amount,
}
