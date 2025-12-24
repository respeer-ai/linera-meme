#![cfg_attr(target_arch = "wasm32", no_main)]

use abi::swap::router::{SwapAbi, SwapOperation};
use async_graphql::{EmptySubscription, Object, Request, Response, Schema};
use linera_sdk::{
    graphql::GraphQLMutationRoot,
    linera_base_types::WithServiceAbi,
    linera_base_types::{ApplicationId, Timestamp},
    views::View,
    Service, ServiceRuntime,
};
use std::sync::Arc;
use swap::state::SwapState;

pub struct SwapService {
    state: Arc<SwapState>,
    runtime: Arc<ServiceRuntime<Self>>,
}

linera_sdk::service!(SwapService);

impl WithServiceAbi for SwapService {
    type Abi = SwapAbi;
}

impl Service for SwapService {
    type Parameters = ();

    async fn new(runtime: ServiceRuntime<Self>) -> Self {
        let state = SwapState::load(runtime.root_view_storage_context())
            .await
            .expect("Failed to load state");
        SwapService {
            state: Arc::new(state),
            runtime: Arc::new(runtime),
        }
    }

    async fn handle_query(&self, request: Request) -> Response {
        let schema = Schema::build(
            QueryRoot {
                state: self.state.clone(),
            },
            SwapOperation::mutation_root(self.runtime.clone()),
            EmptySubscription,
        )
        .finish();
        schema.execute(request).await
    }
}

struct QueryRoot {
    state: Arc<SwapState>,
}

#[Object]
impl QueryRoot {
    async fn applications(
        &self,
        created_before: Option<Timestamp>,
        created_after: Option<Timestamp>,
        application_type: Option<String>,
        spec: Option<String>,
        application_ids: Option<Vec<ApplicationId>>,
        limit: usize,
    ) -> Vec<Metadata> {
        let mut values = Vec::new();
        self.state
            .applications
            .for_each_index_value_while(|_, value| {
                if application_ids.is_some()
                    && !application_ids
                        .clone()
                        .unwrap()
                        .contains(&value.clone().application_id)
                {
                    return Ok(true);
                }
                if spec.is_some()
                    && (!value.spec.is_some()
                        || !value
                            .as_ref()
                            .clone()
                            .spec
                            .unwrap()
                            .to_lowercase()
                            .contains(&format!("\"{}\"", &spec.clone().unwrap().to_lowercase())))
                {
                    return Ok(true);
                }
                if let Some(created_before) = created_before {
                    if value.created_at > created_before {
                        return Ok(true);
                    }
                }
                if let Some(created_after) = created_after {
                    if value.created_at <= created_after {
                        return Ok(true);
                    }
                }
                if let Some(application_type) = application_type.clone() {
                    if value.application_type != application_type {
                        return Ok(true);
                    }
                }
                values.push(value.as_ref().clone());
                Ok(values.len() < limit)
            })
            .await
            .expect("Failed get applications");
        values.sort_by(|a, b| a.created_at.cmp(&b.created_at));
        values
    }

    async fn application(&self, application_id: ApplicationId) -> Option<Metadata> {
        self.state
            .applications
            .get(&application_id)
            .await
            .expect("Failed get application")
    }
}
