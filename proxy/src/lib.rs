// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

/*! ABI of the Proxy Example Application */

use async_graphql::{Request, Response};
use linera_sdk::base::{ContractAbi, ServiceAbi};

pub struct ProxyAbi;

impl ContractAbi for ProxyAbi {
    type Operation = u64;
    type Response = u64;
}

impl ServiceAbi for ProxyAbi {
    type Query = Request;
    type QueryResponse = Response;
}
