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
        Account, Amount, ApplicationId, ChainId, ContractAbi, MessageId, ModuleId, Owner,
        ServiceAbi, Timestamp,
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
    pub owner: Owner,
    pub endpoint: Option<String>,
}

#[derive(Debug, Deserialize, Serialize, Clone)]
pub struct GenesisMiner {
    pub owner: Owner,
    pub endpoint: Option<String>,
    pub approval: Approval,
}

#[derive(Debug, Deserialize, Serialize, Clone, SimpleObject)]
#[serde(rename_all = "camelCase")]
pub struct Chain {
    pub chain_id: ChainId,
    pub message_id: MessageId,
    pub created_at: Timestamp,
    pub token: Option<ApplicationId>,
}

#[derive(Debug, Deserialize, Serialize, GraphQLMutationRoot)]
pub enum ProxyOperation {
    ProposeAddGenesisMiner {
        owner: Owner,
        // Endpoint is used to notify new chain to miner
        endpoint: Option<String>,
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

    // Miner can only register from their client
    RegisterMiner {
        endpoint: Option<String>,
    },
    DeregisterMiner,

    CreateMeme {
        fee_budget: Option<Amount>,
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
        owner: Owner,
        endpoint: Option<String>,
    },
    ApproveAddGenesisMiner {
        operator: Account,
        owner: Owner,
    },

    ProposeRemoveGenesisMiner {
        operator: Account,
        owner: Owner,
    },
    ApproveRemoveGenesisMiner {
        operator: Account,
        owner: Owner,
    },

    RegisterMiner {
        endpoint: Option<String>,
    },
    DeregisterMiner,

    CreateMeme {
        fee_budget: Amount,
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
        owner: Owner,
    },
    ApproveAddOperator {
        operator: Account,
        owner: Owner,
    },

    ProposeBanOperator {
        operator: Account,
        owner: Owner,
    },
    ApproveBanOperator {
        operator: Account,
        owner: Owner,
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
    pub operator: Account,
    pub swap_application_id: ApplicationId,
}
