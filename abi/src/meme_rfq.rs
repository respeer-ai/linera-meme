// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

use async_graphql::{Request, Response};
use linera_sdk::{
    base::{AccountOwner, Amount, ContractAbi, ServiceAbi, ApplicationId, Timestamp},
    graphql::GraphQLMutationRoot,
};
use serde::{Deserialize, Serialize};

pub struct MemeRfqAbi;

impl ContractAbi for MemeRfqAbi {
    type Operation = MemeRfqOperation;
    type Response = MemeRfqResponse;
}

impl ServiceAbi for MemeRfqAbi {
    type Query = Request;
    type QueryResponse = Response;
}

#[derive(Debug, Deserialize, Serialize, GraphQLMutationRoot)]
pub enum MemeRfqOperation {
    FundSuccess,
    FundFailure,
}

#[derive(Debug, Deserialize, Serialize, Default)]
pub enum MemeRfqResponse {
    #[default]
    Ok,
}
