// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

use crate::{
    approval::Approval,
    meme::{InstantiationArgument as MemeInstantiationArgument, MemeParameters},
};
use async_graphql::{Request, Response, SimpleObject};
use linera_sdk::{
    graphql::GraphQLMutationRoot,
    linera_base_types::{
        Account, ApplicationId, ChainId, ContractAbi, ModuleId, ServiceAbi, Timestamp,
    },
};
use serde::{Deserialize, Serialize};

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

#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct Miner {
    pub owner: Account,
}

#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct GenesisMiner {
    pub owner: Account,
    pub approval: Approval,
}

#[derive(Debug, Deserialize, Serialize, Clone, SimpleObject)]
#[serde(rename_all = "camelCase")]
pub struct Chain {
    pub chain_id: ChainId,
    pub created_at: Timestamp,
    pub token: Option<ApplicationId>,
}

#[derive(Debug, Deserialize, Serialize, GraphQLMutationRoot)]
pub enum ProxyOperation {
    ProposeAddGenesisMiner {
        owner: Account,
    },
    ApproveAddGenesisMiner {
        owner: Account,
    },

    ProposeRemoveGenesisMiner {
        owner: Account,
    },
    ApproveRemoveGenesisMiner {
        owner: Account,
    },

    // Miner can only register from their client
    RegisterMiner,
    DeregisterMiner,

    CreateMeme {
        meme_instantiation_argument: MemeInstantiationArgument,
        meme_parameters: MemeParameters,
    },

    ProposeAddOperator {
        owner: Account,
    },
    ApproveAddOperator {
        owner: Account,
    },

    ProposeBanOperator {
        owner: Account,
    },
    ApproveBanOperator {
        owner: Account,
    },
}

#[derive(Debug, Deserialize, Serialize)]
pub enum ProxyMessage {
    ProposeAddGenesisMiner {
        operator: Account,
        owner: Account,
    },
    ApproveAddGenesisMiner {
        operator: Account,
        owner: Account,
    },

    ProposeRemoveGenesisMiner {
        operator: Account,
        owner: Account,
    },
    ApproveRemoveGenesisMiner {
        operator: Account,
        owner: Account,
    },

    RegisterMiner {
        owner: Account,
    },
    DeregisterMiner {
        owner: Account,
    },

    CreateMeme {
        instantiation_argument: MemeInstantiationArgument,
        parameters: MemeParameters,
    },
    CreateMemeExt {
        bytecode_id: ModuleId,
        instantiation_argument: MemeInstantiationArgument,
        parameters: MemeParameters,
    },
    MemeCreated {
        chain_id: ChainId,
        token: ApplicationId,
    },

    ProposeAddOperator {
        operator: Account,
        owner: Account,
    },
    ApproveAddOperator {
        operator: Account,
        owner: Account,
    },

    ProposeBanOperator {
        operator: Account,
        owner: Account,
    },
    ApproveBanOperator {
        operator: Account,
        owner: Account,
    },
}

#[derive(Debug, Deserialize, Serialize, Default)]
pub enum ProxyResponse {
    #[default]
    Ok,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
pub struct InstantiationArgument {
    pub meme_bytecode_id: ModuleId,
    pub operators: Vec<Account>,
    pub swap_application_id: ApplicationId,
}
