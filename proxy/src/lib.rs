// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

use abi::meme::InstantiationArgument as MemeInstantiationArgument;
use async_graphql::{Request, Response};
use linera_sdk::{
    base::{BytecodeId, ContractAbi, Owner, ServiceAbi},
    graphql::GraphQLMutationRoot,
};
use serde::{Deserialize, Serialize};
use thiserror::Error;

pub struct ProxyAbi;

impl ContractAbi for ProxyAbi {
    type Operation = ProxyOperation;
    type Response = ProxyResponse;
}

impl ServiceAbi for ProxyAbi {
    type Query = Request;
    type QueryResponse = Response;
}

/// We don't set any chain for owner because it may be stored on-chain in future

#[derive(Debug, Deserialize, Serialize, GraphQLMutationRoot)]
pub enum ProxyOperation {
    ProposeAddGenesisMiner {
        owner: Owner,
    },
    ApproveAddGenesisMiner {
        owner: Owner,
    },

    ProposeRemoveGenesisMiner {
        owner: Owner,
    },
    ApproveRemoveGenesisMiner {
        owner: Owner,
    },

    RegisterMiner {
        owner: Owner,
    },
    DeregisterMiner {
        owner: Owner,
    },

    CreateMeme {
        meme_instantiation_argument: MemeInstantiationArgument,
    },

    ProposeOperator {
        owner: Owner,
    },
    ApproveOperator {
        owner: Owner,
    },

    SubscribeEvent,
}

#[derive(Debug, Deserialize, Serialize, Default)]
pub enum ProxyResponse {
    #[default]
    Ok,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
pub struct InstantiationArgument {
    pub meme_bytecode_id: BytecodeId,
}

#[derive(Debug, Error)]
#[allow(dead_code)]
pub enum ProxyError {}
