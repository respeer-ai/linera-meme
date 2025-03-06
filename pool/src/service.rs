// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

#![cfg_attr(target_arch = "wasm32", no_main)]

mod state;

use std::sync::Arc;

use abi::swap::pool::PoolAbi;
use async_graphql::{EmptySubscription, Object, Request, Response, Schema};
use linera_sdk::{linera_base_types::WithServiceAbi, views::View, Service, ServiceRuntime};

use self::state::PoolState;

pub struct PoolService {
    state: PoolState,
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
            state,
            runtime: Arc::new(runtime),
        }
    }

    async fn handle_query(&self, request: Request) -> Response {
        let schema = Schema::build(
            QueryRoot {
                value: *self.state.value.get(),
            },
            MutationRoot {
                runtime: self.runtime.clone(),
            },
            EmptySubscription,
        )
        .finish();
        schema.execute(request).await
    }
}

struct MutationRoot {
    runtime: Arc<ServiceRuntime<PoolService>>,
}

#[Object]
impl MutationRoot {
    async fn increment(&self, value: u64) -> [u8; 0] {
        self.runtime.schedule_operation(&value);
        []
    }
}

struct QueryRoot {
    value: u64,
}

#[Object]
impl QueryRoot {
    async fn value(&self) -> &u64 {
        &self.value
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
    fn query() {
        let value = 61_098_721_u64;
        let runtime = Arc::new(ServiceRuntime::<PoolService>::new());
        let mut state = PoolState::load(runtime.root_view_storage_context())
            .blocking_wait()
            .expect("Failed to read from mock key value store");
        state.value.set(value);

        let service = PoolService { state, runtime };
        let request = Request::new("{ value }");

        let response = service
            .handle_query(request)
            .now_or_never()
            .expect("Query should not await anything");

        let expected = Response::new(Value::from_json(json!({"value" : 61_098_721})).unwrap());

        assert_eq!(response, expected)
    }
}
