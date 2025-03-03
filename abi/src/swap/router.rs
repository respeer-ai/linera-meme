// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

use async_graphql::{InputObject, Request, Response};
use linera_sdk::{
    base::{
        Account, AccountOwner, Amount, ApplicationId, BytecodeId, ContractAbi, ServiceAbi,
        Timestamp,
    },
    graphql::GraphQLMutationRoot,
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
}

#[derive(Debug, Deserialize, Serialize)]
pub enum SwapMessage {
    InitializeLiquidity {
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
    CreateRfq {
        rfq_bytecode_id: BytecodeId,
        token_0: ApplicationId,
        token_1: Option<ApplicationId>,
        amount_0: Amount,
        amount_1: Amount,
    },
    CreatePool {
        pool_bytecode_id: BytecodeId,
        token_0: ApplicationId,
        token_1: Option<ApplicationId>,
        amount_0: Amount,
        amount_1: Amount,
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

#[derive(Debug, Clone, Deserialize, Serialize, Eq, PartialEq, InputObject)]
pub struct Pool {
    pub token_0: ApplicationId,
    pub token_1: Option<ApplicationId>,
    pub pool_application: Account,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize, InputObject)]
pub struct InstantiationArgument {
    pub liquidity_rfq_bytecode_id: BytecodeId,
    pub pool_bytecode_id: BytecodeId,
}
