// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

#![cfg_attr(target_arch = "wasm32", no_main)]

use std::sync::Arc;

use abi::pool::{LiquidityAmount, Pool, PoolAbi};
use async_graphql::{EmptyMutation, EmptySubscription, Object, Request, Response, Schema};
use linera_sdk::{
    linera_base_types::{Account, Amount, ApplicationId, ChainId, WithServiceAbi},
    views::View,
    Service, ServiceRuntime,
};

use pool::state::adapter::ServiceStateAdapter;
use pool::state::PoolState;

pub struct PoolService {
    state: Arc<PoolState>,
    runtime: Arc<ServiceRuntime<Self>>,
}

linera_sdk::service!(PoolService);

impl WithServiceAbi for PoolService {
    type Abi = PoolAbi;
}

impl Service for PoolService {
    type Parameters = abi::pool::PoolParameters;

    async fn new(runtime: ServiceRuntime<Self>) -> Self {
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
                state: self.state.clone(),
                runtime: self.runtime.clone(),
            },
            EmptyMutation,
            EmptySubscription,
        )
        .finish();
        schema.execute(request).await
    }
}

struct QueryRoot {
    state: Arc<PoolState>,
    runtime: Arc<ServiceRuntime<PoolService>>,
}

#[Object]
impl QueryRoot {
    async fn health(&self) -> bool {
        true
    }

    async fn creator_chain_id(&self) -> ChainId {
        self.runtime.application_creator_chain_id()
    }

    async fn pool(&self) -> Option<Pool> {
        self.state_adapter()
            .expect("Failed to create pool service state adapter")
            .pool()
            .await
            .expect("Failed to read pool from state")
    }

    async fn claimable_balance(&self, token: Option<ApplicationId>, owner: Account) -> Amount {
        self.state_adapter()
            .expect("Failed to create pool service state adapter")
            .claimable_balance(token, owner)
            .await
            .expect("Failed to read claimable balance from state")
    }

    async fn liquidity(&self, owner: Account) -> LiquidityAmount {
        self.state_adapter()
            .expect("Failed to create pool service state adapter")
            .liquidity(owner)
            .await
            .expect("Failed to read liquidity from state")
    }

    async fn total_supply(&self) -> Amount {
        self.state_adapter()
            .expect("Failed to create pool service state adapter")
            .total_supply()
            .await
            .expect("Failed to read total supply from state")
    }
}

impl QueryRoot {
    fn state_adapter(
        &self,
    ) -> Result<ServiceStateAdapter<PoolService>, pool::state::errors::StateError> {
        ServiceStateAdapter::new(self.runtime.clone(), self.state.clone())
    }
}
