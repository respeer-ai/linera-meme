use async_graphql::{Request, Response};
use linera_sdk::{
    graphql::GraphQLMutationRoot,
    linera_base_types::{Account, Amount, ContractAbi, ServiceAbi},
};
use serde::{Deserialize, Serialize};

pub struct DepositAbi;

impl ContractAbi for DepositAbi {
    type Operation = DepositOperation;
    type Response = DepositResponse;
}

impl ServiceAbi for DepositAbi {
    type Query = Request;
    type QueryResponse = Response;
}

#[derive(Debug, Deserialize, Serialize, GraphQLMutationRoot)]
pub enum DepositOperation {
    Deposit { to: Account, amount: Amount },
}

#[derive(Debug, Deserialize, Serialize, Default)]
pub enum DepositResponse {
    #[default]
    Ok,
}
