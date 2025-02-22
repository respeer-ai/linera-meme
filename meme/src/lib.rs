// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

use async_graphql::{Request, Response};
use linera_sdk::{
    base::{ContractAbi, ServiceAbi, AccountOwner, Amount},
    graphql::GraphQLMutationRoot,
};
use serde::{Deserialize, Serialize};

pub struct MemeAbi;

impl ContractAbi for MemeAbi {
    type Operation = MemeOperation;
    type Response = MemeResponse;
}

impl ServiceAbi for MemeAbi {
    type Query = Request;
    type QueryResponse = Response;
}

#[derive(Debug, Deserialize, Serialize, GraphQLMutationRoot)]
pub enum MemeOperation {
    Transfer {
        to: AccountOwner,
        amount: Amount,
    }
}

#[derive(Debug, Deserialize, Serialize, Default)]
pub enum MemeResponse {
    #[default]
    Ok,
}
