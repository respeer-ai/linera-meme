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
            argument.pool_fee_percent,
            argument.protocol_fee_percent,
            owner,
            timestamp,
        )));
    }

    pub(crate) fn pool(&self) -> Pool {
        self.pool.get().as_ref().unwrap().clone()
    }

    pub(crate) fn initialize_liquidity(
        &mut self,
        amount_0: Amount,
        amount_1: Amount,
        virtual_initial_liquidity: bool,
        block_timestamp: Timestamp,
    ) {
        let mut pool = self.pool();
        if !virtual_initial_liquidity {
            pool.mint_shares(amount_0, amount_1, pool.fee_to);
        }
        pool.liquid(amount_0, amount_1, block_timestamp);
        self.pool.set(Some(pool));
    }
}
