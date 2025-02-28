// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

/*! ABI of the LiquidityRfq Example Application */

use async_graphql::{Request, Response};
use linera_sdk::base::{ContractAbi, ServiceAbi};

pub struct LiquidityRfqAbi;

impl ContractAbi for LiquidityRfqAbi {
    type Operation = u64;
    type Response = u64;
}

impl ServiceAbi for LiquidityRfqAbi {
    type Query = Request;
    type QueryResponse = Response;
}
