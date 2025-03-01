// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

#![cfg_attr(target_arch = "wasm32", no_main)]

mod state;

use std::sync::Arc;

use abi::swap::liquidity_rfq::{LiquidityRfqAbi, LiquidityRfqOperation};
use async_graphql::{EmptySubscription, Object, Request, Response, Schema};
use linera_sdk::{
    base::WithServiceAbi, graphql::GraphQLMutationRoot, views::View, Service, ServiceRuntime,
};

use self::state::LiquidityRfqState;

pub struct LiquidityRfqService {
    state: Arc<LiquidityRfqState>,
    runtime: Arc<ServiceRuntime<Self>>,
}

linera_sdk::service!(LiquidityRfqService);

impl WithServiceAbi for LiquidityRfqService {
    type Abi = LiquidityRfqAbi;
}

impl Service for LiquidityRfqService {
    type Parameters = ();

    async fn new(runtime: ServiceRuntime<Self>) -> Self {
        let state = LiquidityRfqState::load(runtime.root_view_storage_context())
            .await
            .expect("Failed to load state");
        LiquidityRfqService {
            state: Arc::new(state),
            runtime: Arc::new(runtime),
        }
    }

    async fn handle_query(&self, request: Request) -> Response {
        let schema = Schema::build(
            self.state.clone(),
            LiquidityRfqOperation::mutation_root(self.runtime.clone()),
            EmptySubscription,
        )
        .finish();
        schema.execute(request).await
    }
}
