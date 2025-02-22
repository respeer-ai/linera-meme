// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

#![cfg_attr(target_arch = "wasm32", no_main)]

mod state;

use std::sync::Arc;

use async_graphql::{EmptySubscription, Object, Request, Response, Schema};
use linera_sdk::{
    base::{AccountOwner, Amount, WithServiceAbi},
    views::View,
    Service, ServiceRuntime,
};
use meme::MemeOperation;

use self::state::MemeState;

pub struct MemeService {
    state: Arc<MemeState>,
    runtime: Arc<ServiceRuntime<Self>>,
}

linera_sdk::service!(MemeService);

impl WithServiceAbi for MemeService {
    type Abi = meme::MemeAbi;
}

impl Service for MemeService {
    type Parameters = ();

    async fn new(runtime: ServiceRuntime<Self>) -> Self {
        let state = MemeState::load(runtime.root_view_storage_context())
            .await
            .expect("Failed to load state");
        MemeService {
            state: Arc::new(state),
            runtime: Arc::new(runtime),
        }
    }

    async fn handle_query(&self, request: Request) -> Response {
        let schema = Schema::build(
            QueryRoot {
                state: self.state.clone(),
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
    runtime: Arc<ServiceRuntime<MemeService>>,
}

#[Object]
impl MutationRoot {
    async fn transfer(&self, to: AccountOwner, amount: Amount) -> [u8; 0] {
        self.runtime
            .schedule_operation(&MemeOperation::Transfer { to, amount });
        []
    }
}

struct QueryRoot {
    state: Arc<MemeState>,
}

#[Object]
impl QueryRoot {
    async fn total_supply(&self) -> Amount {
        self.state.meme.get().as_ref().unwrap().total_supply
    }
}

#[cfg(test)]
mod tests {
    use std::sync::Arc;

    use async_graphql::{Request, Response, Value};
    use futures::FutureExt as _;
    use linera_sdk::{util::BlockingWait, views::View, Service, ServiceRuntime};
    use serde_json::json;

    use super::{MemeService, MemeState};

    #[test]
    fn query() {
        let value = 61_098_721_u64;
        let runtime = Arc::new(ServiceRuntime::<MemeService>::new());
        let mut state = MemeState::load(runtime.root_view_storage_context())
            .blocking_wait()
            .expect("Failed to read from mock key value store");
        state.value.set(value);

        let service = MemeService { state, runtime };
        let request = Request::new("{ value }");

        let response = service
            .handle_query(request)
            .now_or_never()
            .expect("Query should not await anything");

        let expected = Response::new(Value::from_json(json!({"value" : 61_098_721})).unwrap());

        assert_eq!(response, expected)
    }
}
