// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

#![cfg_attr(target_arch = "wasm32", no_main)]

mod state;

use std::sync::Arc;

use abi::swap::pool::{Pool, PoolAbi};
use async_graphql::{EmptyMutation, EmptySubscription, Object, Request, Response, Schema};
use linera_sdk::{linera_base_types::WithServiceAbi, views::View, Service, ServiceRuntime};

use self::state::PoolState;

pub struct PoolService {
    state: Arc<PoolState>,
    runtime: Arc<ServiceRuntime<Self>>,
}

linera_sdk::service!(PoolService);

impl WithServiceAbi for PoolService {
    type Abi = PoolAbi;
}

impl Service for PoolService {
    type Parameters = ();

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
}

#[Object]
impl QueryRoot {
    async fn pool(&self) -> Pool {
        self.state.pool.get().as_ref().unwrap().clone()
    }
}

#[cfg(test)]
mod tests {
    use std::sync::Arc;

    use async_graphql::{Request, Response, Value};
    use futures::FutureExt as _;
    use linera_sdk::{util::BlockingWait, views::View, Service, ServiceRuntime};
    use serde_json::json;

    use super::{PoolService, PoolState};

    #[test]
    fn query() {}
}
