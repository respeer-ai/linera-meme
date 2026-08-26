// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

use super::abi::InitializeArgument;
use async_graphql::{Request, Response};
use linera_sdk::{
    graphql::GraphQLMutationRoot,
    linera_base_types::{
        Account, AccountOwner, ApplicationId, ChainId, ContractAbi, ModuleId, ServiceAbi,
        Timestamp,
    },
};
use serde::{Deserialize, Serialize};

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
pub struct StateInstantiationArgument {
    pub business_application_id: ApplicationId,
    pub operator: Option<Account>,
}

pub struct ProxyStateAbi;

impl ContractAbi for ProxyStateAbi {
    type Operation = ProxyStateV1Operation;
    type Response = ProxyStateV1Response;
}

impl ServiceAbi for ProxyStateAbi {
    type Query = Request;
    type QueryResponse = Response;
}

#[derive(Debug, Clone, Deserialize, Eq, PartialEq, Serialize, GraphQLMutationRoot)]
pub enum ProxyStateV1Operation {
    Initialize {
        argument: InitializeArgument,
    },

    SetMemeBytecodeIds {
        business_bytecode_id: ModuleId,
        state_bytecode_id: ModuleId,
    },

    AddOperator { owner: Account },
    ApproveAddOperator { owner: Account, operator: Account },
    BanOperator { owner: Account },
    ApproveBanOperator { owner: Account, operator: Account },

    AddGenesisMiner { owner: Account },
    ApproveAddGenesisMiner { owner: Account, operator: Account },
    RemoveGenesisMiner { owner: Account },
    ApproveRemoveGenesisMiner { owner: Account, operator: Account },

    RegisterMiner { owner: Account, now: Timestamp },
    DeregisterMiner { owner: Account },

    CreateChain { chain_id: ChainId, created_at: Timestamp },
    CreateChainToken { chain_id: ChainId, token: ApplicationId },

    MemeBytecodeId,
    MemeStateBytecodeIds,
    SwapApplicationId,
    IsGenesisMiner { owner: Account },
    Miners,
    MinerOwners,
    GenesisMiners,
    Chain { chain_id: ChainId },
    Chains { created_after: Option<Timestamp> },
    ChainByToken { token: ApplicationId },

    ValidateOperator { owner: Account },

    SetOperator { new_operator: Account },

    Handoff {
        new_business_application_id: ApplicationId,
    },
}

#[derive(Debug, Clone, Deserialize, Eq, PartialEq, Serialize)]
pub enum ProxyStateV1Response {
    Ok,
    Fail(String),
    Bool(bool),
    ModuleId(ModuleId),
    ModuleIds(Vec<(u16, ModuleId)>),
    ApplicationId(ApplicationId),
    Miner(super::Miner),
    Miners(Vec<super::Miner>),
    AccountOwners(Vec<AccountOwner>),
    Chain(Option<super::Chain>),
    Chains(Vec<super::Chain>),
}
