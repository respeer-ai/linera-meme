// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

use abi::swap::pool::{InstantiationArgument, Pool, PoolParameters};
use linera_sdk::{
    linera_base_types::{Account, Amount, ApplicationId, Timestamp},
    views::{linera_views, RegisterView, RootView, ViewStorageContext},
};

/// The application state.
#[derive(RootView)]
#[view(context = "ViewStorageContext")]
pub struct PoolState {
    pub pool: RegisterView<Option<Pool>>,
    pub router_application_id: RegisterView<Option<ApplicationId>>,
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
        self.router_application_id
            .set(Some(argument.router_application_id));
    }

    pub(crate) fn pool(&self) -> Pool {
        self.pool.get().as_ref().unwrap().clone()
    }

    pub(crate) fn router_application_id(&self) -> ApplicationId {
        self.router_application_id.get().unwrap()
    }

    pub(crate) fn token_0(&self) -> ApplicationId {
        self.pool.get().as_ref().unwrap().token_0
    }

    pub(crate) fn token_1(&self) -> Option<ApplicationId> {
        self.pool.get().as_ref().unwrap().token_1
    }
}
