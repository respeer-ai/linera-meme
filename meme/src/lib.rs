// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

use async_graphql::{Request, Response};
use linera_sdk::base::{ContractAbi, ServiceAbi};

pub struct MemeAbi;

impl ContractAbi for MemeAbi {
    type Operation = u64;
    type Response = u64;
}

impl ServiceAbi for MemeAbi {
    type Query = Request;
    type QueryResponse = Response;
}
