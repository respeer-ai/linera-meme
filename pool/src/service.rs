// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

#![cfg_attr(target_arch = "wasm32", no_main)]

mod state;

use std::{str::FromStr, sync::Arc};

use abi::swap::{
    pool::{Pool, PoolAbi, PoolParameters},
    transaction::Transaction,
};
use async_graphql::{EmptyMutation, EmptySubscription, Object, Request, Response, Schema};
use linera_sdk::{
    linera_base_types::{Account, Amount, WithServiceAbi},
    views::View,
    Service, ServiceRuntime,
};

use self::state::PoolState;

#[derive(Clone)]
pub struct PoolService {
    state: Arc<PoolState>,
    runtime: Arc<ServiceRuntime<Self>>,
}

linera_sdk::service!(PoolService);

impl WithServiceAbi for PoolService {
    type Abi = PoolAbi;
}

impl Service for PoolService {
    type Parameters = PoolParameters;

    async fn new(runtime: ServiceRuntime<Self>) -> Self {
        let _ = runtime.application_parameters();

        let state = PoolState::load(runtime.root_view_storage_context())
            .await
            .expect("Failed to load state");
        PoolService {
            state: Arc::new(state),
            runtime: Arc::new(runtime),
        }
    }

    async fn handle_query(&self, request: Request) -> Response {
        let schema = Schema::build(
            QueryRoot {
                service: self.clone(),
            },
            EmptyMutation,
            EmptySubscription,
        )
        .finish();
        schema.execute(request).await
    }
}

impl PoolService {
    fn virtual_initial_liquidity(&self) -> bool {
        self.runtime
            .application_parameters()
            .virtual_initial_liquidity
    }

    fn state(&self) -> Arc<PoolState> {
        self.state.clone()
    }
}

struct QueryRoot {
    service: PoolService,
}

#[Object]
impl QueryRoot {
    async fn pool(&self) -> Pool {
        self.service.state().pool()
    }

    // async fn liquidity(&self, owner: Account) -> Amount {
    async fn liquidity(&self, owner: String) -> Amount {
        self.service
            .state()
            .liquidity(Account::from_str(&owner).unwrap())
            .await
            .unwrap()
    }

    async fn virtual_initial_liquidity(&self) -> bool {
        self.service.virtual_initial_liquidity()
    }

    async fn latest_transactions(&self, start_id: Option<u32>) -> Vec<Transaction> {
        let mut transactions: Vec<_> = self
            .service
            .state()
            .latest_transactions
            .elements()
            .await
            .expect("Failed get transactions")
            .into_iter()
            .filter(|transaction| transaction.transaction_id >= start_id)
            .collect();
        transactions.sort_by(|a, b| a.created_at.cmp(&b.created_at));
        transactions
    }
}

#[cfg(test)]
mod tests {
    #[test]
    fn query() {}
}
