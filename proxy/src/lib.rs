// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

use async_graphql::{Request, Response};
use linera_sdk::base::{ContractAbi, ServiceAbi};

pub struct ProxyAbi;

impl ContractAbi for ProxyAbi {
    type Operation = Operation;
    type Response = u64;
}

impl ServiceAbi for ProxyAbi {
    type Query = Request;
    type QueryResponse = Response;
}

#[derive(Debug, Deserialize, Serialize, GraphQLMutationRoot)]
pub enum Operation {
    RegisterGenesisMiner { owner: Owner },
    DeregisterGenesisMiner { owner: Owner },
    RegisterMiner { owner: Owner },
    DeregisterMiner { owner: Owner },
    CreateMeme {},
    SubscribeEvent,
}
