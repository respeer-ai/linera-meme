// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

use async_graphql::{scalar, Request, Response};
use linera_sdk::{
    graphql::GraphQLMutationRoot,
    linera_base_types::{Amount, ApplicationId, ContractAbi, ServiceAbi},
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
    Approved { token: ApplicationId },
    Rejected { token: ApplicationId },
}

#[derive(Debug, Deserialize, Serialize, Default)]
pub enum LiquidityRfqResponse {
    #[default]
    Ok,
}

#[derive(Clone, Copy, Debug, Deserialize, Serialize)]
pub struct LiquidityRfqParameters {
    pub token_0: ApplicationId,
    pub token_1: Option<ApplicationId>,
    pub amount_0: Amount,
    pub amount_1: Amount,
    pub router_application_id: ApplicationId,
}

scalar!(LiquidityRfqParameters);
