// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

#![cfg_attr(target_arch = "wasm32", no_main)]

mod state;

use std::sync::Arc;

use async_graphql::{EmptySubscription, Object, Request, Response, Schema};
use linera_sdk::{base::WithServiceAbi, views::View, Service, ServiceRuntime};

use self::state::LiquidityRfqState;

pub struct LiquidityRfqService {
    state: LiquidityRfqState,
    runtime: Arc<ServiceRuntime<Self>>,
}

linera_sdk::service!(LiquidityRfqService);

impl WithServiceAbi for LiquidityRfqService {
    type Abi = liquidity_rfq::LiquidityRfqAbi;
}

impl Service for LiquidityRfqService {
    type Parameters = ();

    async fn new(runtime: ServiceRuntime<Self>) -> Self {
        let state = LiquidityRfqState::load(runtime.root_view_storage_context())
            .await
            .expect("Failed to load state");
        LiquidityRfqService {
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
    runtime: Arc<ServiceRuntime<LiquidityRfqService>>,
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

    use super::{LiquidityRfqService, LiquidityRfqState};

    #[test]
    fn query() {
        let value = 61_098_721_u64;
        let runtime = Arc::new(ServiceRuntime::<LiquidityRfqService>::new());
        let mut state = LiquidityRfqState::load(runtime.root_view_storage_context())
            .blocking_wait()
            .expect("Failed to read from mock key value store");
        state.value.set(value);

        let service = LiquidityRfqService { state, runtime };
        let request = Request::new("{ value }");

        let response = service
            .handle_query(request)
            .now_or_never()
            .expect("Query should not await anything");

        let expected = Response::new(Value::from_json(json!({"value" : 61_098_721})).unwrap());

        assert_eq!(response, expected)
    }
}
