// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

use async_graphql::{scalar, InputObject, Request, Response, SimpleObject};
use linera_sdk::{
    graphql::GraphQLMutationRoot,
    linera_base_types::{
        Account, AccountOwner, Amount, ApplicationId, ChainId, ContractAbi, ModuleId, ServiceAbi,
        Timestamp,
    },
};
use serde::{Deserialize, Serialize};

pub struct SwapAbi;

impl ContractAbi for SwapAbi {
    type Operation = SwapOperation;
    type Response = SwapResponse;
}

impl ServiceAbi for SwapAbi {
    type Query = Request;
    type QueryResponse = Response;
}

#[derive(Debug, Deserialize, Serialize, GraphQLMutationRoot)]
pub enum SwapOperation {
    // Token 1 can only be native token when initializing
    InitializeLiquidity {
        // TODO: use to avoid reentrant invocation before
        // https://github.com/linera-io/linera-protocol/issues/3538 being fixed
        token_0_creator_chain_id: ChainId,
        token_0: ApplicationId,
        amount_0: Amount,
        amount_1: Amount,
        // Only for creator to initialize pool
        virtual_liquidity: bool,
        to: Option<AccountOwner>,
    },
    AddLiquidity {
        token_0: ApplicationId,
        token_1: Option<ApplicationId>,
        amount_0_desired: Amount,
        amount_1_desired: Amount,
        amount_0_min: Amount,
        amount_1_min: Amount,
        to: Option<AccountOwner>,
        deadline: Option<Timestamp>,
    },
    LiquidityFundApproved {
        token_0: ApplicationId,
        token_1: Option<ApplicationId>,
        amount_0_desired: Amount,
        amount_1_desired: Amount,
        amount_0_min: Amount,
        amount_1_min: Amount,
        to: Option<AccountOwner>,
        deadline: Option<Timestamp>,
    },
    RemoveLiquidity {
        token_0: ApplicationId,
        token_1: Option<ApplicationId>,
        liquidity: Amount,
        amount_0_min: Amount,
        amount_1_min: Amount,
        to: Option<AccountOwner>,
        deadline: Option<Timestamp>,
    },
    Swap {
        token_0: ApplicationId,
        token_1: Option<ApplicationId>,
        amount_0_in: Option<Amount>,
        amount_1_in: Option<Amount>,
        amount_0_out_min: Option<Amount>,
        amount_1_out_min: Option<Amount>,
        to: Option<AccountOwner>,
        deadline: Option<Timestamp>,
    },
}

#[derive(Debug, Deserialize, Serialize, Default)]
pub enum SwapResponse {
    #[default]
    Ok,
    ChainId(ChainId),
}

#[derive(Debug, Deserialize, Serialize)]
pub enum SwapMessage {
    InitializeLiquidity {
        // TODO: use to avoid reentrant invocation before
        // https://github.com/linera-io/linera-protocol/issues/3538 being fixed
        token_0_creator_chain_id: ChainId,
        token_0: ApplicationId,
        amount_0: Amount,
        amount_1: Amount,
        // Only for creator to initialize pool
        virtual_liquidity: bool,
        to: Option<AccountOwner>,
    },
    AddLiquidity {
        token_0: ApplicationId,
        token_1: Option<ApplicationId>,
        amount_0_desired: Amount,
        amount_1_desired: Amount,
        amount_0_min: Amount,
        amount_1_min: Amount,
        to: Option<AccountOwner>,
        deadline: Option<Timestamp>,
    },
    CreatePool {
        pool_bytecode_id: ModuleId,
        // TODO: use to avoid reentrant invocation before
        // https://github.com/linera-io/linera-protocol/issues/3538 being fixed
        token_0_creator_chain_id: ChainId,
        token_0: ApplicationId,
        token_1_creator_chain_id: Option<ChainId>,
        token_1: Option<ApplicationId>,
        amount_0: Amount,
        amount_1: Amount,
        virtual_initial_liquidity: bool,
    },
    PoolCreated {
        pool_application: Account,
        token_0: ApplicationId,
        token_1: Option<ApplicationId>,
        amount_0: Amount,
        amount_1: Amount,
        virtual_initial_liquidity: bool,
    },
    LiquidityFundApproved {
        token_0: ApplicationId,
        token_1: Option<ApplicationId>,
        amount_0_desired: Amount,
        amount_1_desired: Amount,
        amount_0_min: Amount,
        amount_1_min: Amount,
        to: Option<AccountOwner>,
        deadline: Option<Timestamp>,
    },
    RemoveLiquidity {
        token_0: ApplicationId,
        token_1: Option<ApplicationId>,
        liquidity: Amount,
        amount_0_min: Amount,
        amount_1_min: Amount,
        to: Option<AccountOwner>,
        deadline: Option<Timestamp>,
    },
    Swap {
        token_0: ApplicationId,
        token_1: Option<ApplicationId>,
        amount_0_in: Option<Amount>,
        amount_1_in: Option<Amount>,
        amount_0_out_min: Option<Amount>,
        amount_1_out_min: Option<Amount>,
        to: Option<AccountOwner>,
        deadline: Option<Timestamp>,
    },
}

#[derive(Debug, Clone, Deserialize, Serialize, Eq, PartialEq, SimpleObject)]
#[serde(rename_all = "camelCase")]
pub struct Pool {
    pub pool_id: u64,
    pub token_0: ApplicationId,
    pub token_1: Option<ApplicationId>,
    pub pool_application: Account,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize, InputObject)]
pub struct InstantiationArgument {
    pub pool_bytecode_id: ModuleId,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
pub struct SwapParameters {}

scalar!(SwapParameters);
