#![cfg_attr(target_arch = "wasm32", no_main)]

use abi::ams::{AmsAbi, AmsOperation};
use ams::state::AmsState;
use async_graphql::{EmptySubscription, Request, Response, Schema};
use linera_sdk::{
    graphql::GraphQLMutationRoot, linera_base_types::WithServiceAbi, views::View, Service,
    ServiceRuntime,
};
use std::sync::Arc;

pub struct AmsService {
    state: Arc<AmsState>,
    runtime: Arc<ServiceRuntime<Self>>,
}

linera_sdk::service!(AmsService);

impl WithServiceAbi for AmsService {
    type Abi = AmsAbi;
}

impl Service for AmsService {
    type Parameters = ();

    async fn new(runtime: ServiceRuntime<Self>) -> Self {
        let state = AmsState::load(runtime.root_view_storage_context())
            .await
            .expect("Failed to load state");
        AmsService {
            state: Arc::new(state),
            runtime: Arc::new(runtime),
        }
    }

    async fn handle_query(&self, request: Request) -> Response {
        let schema = Schema::build(
            self.state.clone(),
            AmsOperation::mutation_root(self.runtime.clone()),
            EmptySubscription,
        )
        .finish();
        schema.execute(request).await
    }
}
