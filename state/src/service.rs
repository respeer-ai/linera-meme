#![cfg_attr(target_arch = "wasm32", no_main)]

use abi::state::StateAbi;
use async_graphql::{EmptyMutation, EmptySubscription, Object, Request, Response, Schema};
use linera_sdk::{linera_base_types::WithServiceAbi, views::View, Service, ServiceRuntime};
use state::state::State;
use std::sync::Arc;

pub struct StateService {
    _state: Arc<State>,
}

linera_sdk::service!(StateService);

impl WithServiceAbi for StateService {
    type Abi = StateAbi;
}

impl Service for StateService {
    type Parameters = ();

    async fn new(runtime: ServiceRuntime<Self>) -> Self {
        let state = State::load(runtime.root_view_storage_context())
            .await
            .expect("Failed to load state");
        StateService {
            _state: Arc::new(state),
        }
    }

    async fn handle_query(&self, request: Request) -> Response {
        let schema = Schema::build(QueryRoot, EmptyMutation, EmptySubscription).finish();
        schema.execute(request).await
    }
}

struct QueryRoot;

#[Object]
impl QueryRoot {
    async fn ready(&self) -> bool {
        true
    }
}
