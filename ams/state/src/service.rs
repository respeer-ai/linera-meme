#![cfg_attr(target_arch = "wasm32", no_main)]

use abi::ams::state_v1::AmsStateAbi;
use async_graphql::{EmptyMutation, EmptySubscription, Object, Request, Response, Schema};
use linera_sdk::{linera_base_types::WithServiceAbi, Service, ServiceRuntime};

pub struct AmsStateService;

linera_sdk::service!(AmsStateService);

impl WithServiceAbi for AmsStateService {
    type Abi = AmsStateAbi;
}

impl Service for AmsStateService {
    type Parameters = ();

    async fn new(_runtime: ServiceRuntime<Self>) -> Self {
        Self
    }

    async fn handle_query(&self, request: Request) -> Response {
        Schema::build(QueryRoot, EmptyMutation, EmptySubscription)
            .finish()
            .execute(request)
            .await
    }
}

struct QueryRoot;

#[Object]
impl QueryRoot {
    async fn health(&self) -> bool {
        true
    }
}
