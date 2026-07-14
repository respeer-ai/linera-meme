#![cfg_attr(target_arch = "wasm32", no_main)]

use abi::ams::{abi::Metadata, state_v1::AmsStateAbi};
use ams_state::state::AmsState;
use async_graphql::{EmptyMutation, EmptySubscription, Object, Request, Response, Schema};
use linera_sdk::{
    linera_base_types::{ApplicationId, WithServiceAbi},
    views::View,
    Service, ServiceRuntime,
};
use std::sync::Arc;

pub struct AmsStateService {
    state: Arc<AmsState>,
}

linera_sdk::service!(AmsStateService);

impl WithServiceAbi for AmsStateService {
    type Abi = AmsStateAbi;
}

impl Service for AmsStateService {
    type Parameters = ();

    async fn new(runtime: ServiceRuntime<Self>) -> Self {
        let state = AmsState::load(runtime.root_view_storage_context())
            .await
            .expect("Failed to load AMS StateV1 state");
        Self {
            state: Arc::new(state),
        }
    }

    async fn handle_query(&self, request: Request) -> Response {
        Schema::build(
            QueryRoot {
                state: self.state.clone(),
            },
            EmptyMutation,
            EmptySubscription,
        )
        .finish()
        .execute(request)
        .await
    }
}

struct QueryRoot {
    state: Arc<AmsState>,
}

#[Object]
impl QueryRoot {
    async fn health(&self) -> bool {
        true
    }

    async fn application(&self, application_id: ApplicationId) -> Option<Metadata> {
        self.state
            .applications
            .get(&application_id)
            .await
            .expect("Failed to read application from state")
    }

    async fn applications(&self) -> Vec<Metadata> {
        self.state
            .applications
            .index_values()
            .await
            .expect("Failed to read applications from state")
            .into_iter()
            .map(|(_, metadata)| metadata)
            .collect()
    }

    async fn business_application_id(&self) -> Option<ApplicationId> {
        *self.state.business_application_id.get()
    }
}

#[cfg(test)]
mod service_tests {
    use super::*;
    use async_graphql::Value;
    use linera_sdk::{util::BlockingWait, views::View};
    use serde_json::json;
    use std::str::FromStr;

    #[tokio::test(flavor = "multi_thread")]
    async fn business_application_id_query_reads_state_register() {
        let business_id =
            application_id("a10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bad");
        let runtime = ServiceRuntime::<AmsStateService>::new();
        let mut state = AmsState::load(runtime.root_view_storage_context())
            .blocking_wait()
            .expect("Failed to read AMS StateV1 state");
        state.business_application_id.set(Some(business_id));

        let service = AmsStateService {
            state: Arc::new(state),
        };

        let response = service
            .handle_query(Request::new("{ businessApplicationId }"))
            .await;

        let expected = Response::new(
            Value::from_json(json!({ "businessApplicationId": business_id })).unwrap(),
        );
        assert_eq!(response, expected);
    }

    fn application_id(value: &str) -> ApplicationId {
        ApplicationId::from_str(value).unwrap()
    }
}
