// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

use async_graphql::{Request, Response, scalar};
use linera_sdk::{
    base::{AccountOwner, Amount, ContractAbi, ServiceAbi, ApplicationId, Timestamp},
    graphql::GraphQLMutationRoot,
};
use serde::{Deserialize, Serialize};

pub struct LiquidityRfqAbi;

impl ContractAbi for LiquidityRfqAbi {
    type Operation = LiquidityRfqOperation;
    type Response = LiquidityRfqResponse;
}

impl ServiceAbi for LiquidityRfqAbi {
    type Query = Request;
    type QueryResponse = Response;
}

#[derive(Debug, Deserialize, Serialize, GraphQLMutationRoot)]
pub enum LiquidityRfqOperation {
    FundSuccess,
    FundFailure,
}

#[derive(Debug, Deserialize, Serialize, Default)]
pub enum LiquidityRfqResponse {
    #[default]
    Ok,
}

#[derive(Clone, Copy, Debug, Deserialize, Serialize)]
pub struct LiquidityRfqParameters {}

scalar!(LiquidityRfqParameters);
