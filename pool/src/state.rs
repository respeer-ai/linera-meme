// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

use abi::swap::pool::{InstantiationArgument, Pool, PoolParameters};
use linera_sdk::{
    linera_base_types::{Account, Amount, Timestamp},
    views::{linera_views, RegisterView, RootView, ViewStorageContext},
};

/// The application state.
#[derive(RootView)]
#[view(context = "ViewStorageContext")]
pub struct PoolState {
    pub pool: RegisterView<Option<Pool>>,
}

#[allow(dead_code)]
impl PoolState {
    pub(crate) fn instantiate(
        &mut self,
        argument: InstantiationArgument,
        parameters: PoolParameters,
        owner: Account,
        timestamp: Timestamp,
    ) {
        self.pool.set(Some(Pool::create(
            parameters.token_0,
            parameters.token_1,
            parameters.virtual_initial_liquidity,
            argument.amount_0,
            argument.amount_1,
            argument.pool_fee_percent,
            argument.protocol_fee_percent,
            owner,
            timestamp,
        )));
    }

    pub(crate) fn pool(&self) -> Pool {
        self.pool.get().as_ref().unwrap().clone()
    }
}
