// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

use async_graphql::{scalar, InputObject, Request, Response, SimpleObject};
use linera_sdk::{
    graphql::GraphQLMutationRoot,
    linera_base_types::{
        Account, Amount, ApplicationId, ChainId, ContractAbi, ModuleId, ServiceAbi, Timestamp,
    },
};
use serde::{Deserialize, Serialize};

use crate::swap::transaction::Transaction;

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
        creator: Account,
        // TODO: use to avoid reentrant invocation before
        // https://github.com/linera-io/linera-protocol/issues/3538 being fixed
        token_0_creator_chain_id: ChainId,
        token_0: ApplicationId,
        amount_0: Amount,
        amount_1: Amount,
        // Only for creator to initialize pool
        virtual_liquidity: bool,
        to: Option<Account>,
    },
    // User can only create meme meme pair. Meme native pair is created by creator
    CreatePool {
        // TODO: use to avoid reentrant invocation before
        // https://github.com/linera-io/linera-protocol/issues/3538 being fixed
        token_0_creator_chain_id: ChainId,
        token_0: ApplicationId,
        token_1_creator_chain_id: Option<ChainId>,
        token_1: Option<ApplicationId>,
        amount_0: Amount,
        amount_1: Amount,
        to: Option<Account>,
    },
    // Notify swap of new transaction, called from pool chain
    UpdatePool {
        token_0: ApplicationId,
        token_1: Option<ApplicationId>,
        transaction: Transaction,
        token_0_price: Amount,
        token_1_price: Amount,
        reserve_0: Amount,
        reserve_1: Amount,
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
        creator: Account,
        // TODO: use to avoid reentrant invocation before
        // https://github.com/linera-io/linera-protocol/issues/3538 being fixed
        token_0_creator_chain_id: ChainId,
        token_0: ApplicationId,
        amount_0: Amount,
        amount_1: Amount,
        // Only for creator to initialize pool
        virtual_liquidity: bool,
        to: Option<Account>,
    },
    CreatePool {
        creator: Account,
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
        to: Option<Account>,
        user_pool: bool,
    },
    PoolCreated {
        creator: Account,
        pool_application: Account,
        token_0: ApplicationId,
        token_1: Option<ApplicationId>,
        amount_0: Amount,
        amount_1: Amount,
        virtual_initial_liquidity: bool,
        to: Option<Account>,
        user_pool: bool,
    },
    // Execute on swap creation chain
    CreateUserPool {
        // TODO: use to avoid reentrant invocation before
        // https://github.com/linera-io/linera-protocol/issues/3538 being fixed
        token_0_creator_chain_id: ChainId,
        token_0: ApplicationId,
        // It should be option for mining only meme
        token_1_creator_chain_id: Option<ChainId>,
        token_1: Option<ApplicationId>,
        amount_0: Amount,
        amount_1: Amount,
        to: Option<Account>,
    },
    // Execute on user caller chain
    UserPoolCreated {
        pool_application: Account,
        token_0: ApplicationId,
        token_1: Option<ApplicationId>,
        amount_0: Amount,
        amount_1: Amount,
        to: Option<Account>,
    },
    UpdatePool {
        token_0: ApplicationId,
        token_1: Option<ApplicationId>,
        transaction: Transaction,
        token_0_price: Amount,
        token_1_price: Amount,
        reserve_0: Amount,
        reserve_1: Amount,
    },
}

#[derive(Debug, Clone, Deserialize, Serialize, Eq, PartialEq, SimpleObject)]
#[serde(rename_all = "camelCase")]
pub struct Pool {
    pub pool_id: u64,
    pub creator: Account,
    pub token_0: ApplicationId,
    pub token_1: Option<ApplicationId>,
    pub pool_application: Account,
    pub latest_transaction: Option<Transaction>,
    pub token_0_price: Option<Amount>,
    pub token_1_price: Option<Amount>,
    pub reserve_0: Option<Amount>,
    pub reserve_1: Option<Amount>,
    pub created_at: Timestamp,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize, InputObject)]
pub struct InstantiationArgument {
    pub pool_bytecode_id: ModuleId,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
pub struct SwapParameters {}

scalar!(SwapParameters);
