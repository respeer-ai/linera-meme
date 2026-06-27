#![cfg_attr(target_arch = "wasm32", no_main)]

use abi::ams::{AmsAbi, Metadata};
use ams::state::{adapter::ServiceStateAdapter, AmsState};
use async_graphql::{EmptyMutation, EmptySubscription, Object, Request, Response, Schema};
use linera_sdk::{
    linera_base_types::WithServiceAbi,
    linera_base_types::{ApplicationId, Timestamp},
    views::View,
    Service, ServiceRuntime,
};
use std::sync::Arc;

pub struct AmsService {
    runtime: Arc<ServiceRuntime<Self>>,
    state: Arc<AmsState>,
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
            runtime: Arc::new(runtime),
            state: Arc::new(state),
        }
    }
    async fn handle_query(&self, request: Request) -> Response {
        let schema = Schema::build(
            QueryRoot {
                runtime: self.runtime.clone(),
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
    runtime: Arc<ServiceRuntime<AmsService>>,
    state: Arc<AmsState>,
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
        let mut values = self
            .state_adapter()
            .expect("Failed to create AMS service state adapter")
            .applications()
            .expect("Failed to read AMS applications from state")
            .into_iter()
            .filter(|value| {
                if let Some(application_ids) = &application_ids {
                    if !application_ids.contains(&value.application_id) {
                        return false;
                    }
                }
                if let Some(spec) = &spec {
                    if !value
                        .spec
                        .as_ref()
                        .map(|value| {
                            value
                                .to_lowercase()
                                .contains(&format!("\"{}\"", spec.to_lowercase()))
                        })
                        .unwrap_or(false)
                    {
                        return false;
                    }
                }
                if let Some(created_before) = created_before {
                    if value.created_at > created_before {
                        return false;
                    }
                }
                if let Some(created_after) = created_after {
                    if value.created_at <= created_after {
                        return false;
                    }
                }
                if let Some(application_type) = &application_type {
                    if &value.application_type != application_type {
                        return false;
                    }
                }
                true
            })
            .collect::<Vec<_>>();
        values.sort_by(|a, b| a.created_at.cmp(&b.created_at));
        values.truncate(limit);
        values
    }

    async fn application(&self, application_id: ApplicationId) -> Option<Metadata> {
        self.state_adapter()
            .expect("Failed to create AMS service state adapter")
            .application(application_id)
            .expect("Failed to read AMS application from state")
    }
}

impl QueryRoot {
    fn state_adapter(
        &self,
    ) -> Result<ServiceStateAdapter<AmsService>, ams::state::errors::StateError> {
        ServiceStateAdapter::new(self.runtime.clone(), self.state.clone())
    }
}

#[cfg(test)]
mod service_tests {
    use super::*;
    use abi::{ams::AmsAbi, store_type::StoreType};
    use async_graphql::Value;
    use linera_sdk::bcs;
    use linera_sdk::{
        linera_base_types::{
            Account, AccountOwner, ApplicationId, ChainId, CryptoHash, TestString,
        },
        util::BlockingWait,
    };
    use serde_json::json;
    use std::str::FromStr;

    #[tokio::test(flavor = "multi_thread")]
    async fn application_query_reads_state_application() {
        let metadata = test_metadata(
            application_id("b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bae"),
            "Meme",
        );
        let metadata_for_query = metadata.clone();
        let runtime = runtime_with_state_query(move |query| {
            assert_eq!(query, "read");
            Response::new(
                Value::from_json(json!({
                    "read": bcs::to_bytes(&metadata_for_query).unwrap(),
                }))
                .unwrap(),
            )
        });
        let service = service_with_runtime(runtime);

        let response = service
            .handle_query(Request::new(format!(
                "{{ application(applicationId: \"{}\") }}",
                metadata.application_id
            )))
            .await;

        let expected = Response::new(Value::from_json(json!({ "application": metadata })).unwrap());
        assert_eq!(response, expected);
    }

    #[tokio::test(flavor = "multi_thread")]
    async fn applications_query_batch_reads_state_applications_index() {
        let metadata = test_metadata(
            application_id("b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bae"),
            "Meme",
        );
        let metadata_for_query = metadata.clone();
        let mut read_count = 0;
        let runtime = runtime_with_state_query(move |query| {
            read_count += 1;
            match read_count {
                1 => {
                    assert_eq!(query, "read");
                    Response::new(
                        Value::from_json(json!({
                            "read": bcs::to_bytes(&vec![metadata_for_query.application_id]).unwrap(),
                        }))
                        .unwrap(),
                    )
                }
                2 => {
                    assert_eq!(query, "batchRead");
                    Response::new(
                        Value::from_json(json!({
                            "batchRead": vec![bcs::to_bytes(&metadata_for_query).unwrap()],
                        }))
                        .unwrap(),
                    )
                }
                _ => panic!("unexpected state query"),
            }
        });
        let service = service_with_runtime(runtime);

        let response = service
            .handle_query(Request::new("{ applications(limit: 10) }"))
            .await;

        let expected =
            Response::new(Value::from_json(json!({ "applications": vec![metadata] })).unwrap());
        assert_eq!(response, expected);
    }

    fn runtime_with_state_query(
        mut response_for_query: impl FnMut(&str) -> Response + Send + 'static,
    ) -> Arc<ServiceRuntime<AmsService>> {
        let runtime = ServiceRuntime::<AmsService>::new()
            .with_application_id(ams_application_id().with_abi::<AmsAbi>())
            .with_query_application_handler(move |application_id, query| {
                assert_eq!(application_id, state_application_id());
                let request: Request = serde_json::from_slice(&query).unwrap();
                let query_name = if request.query.contains("batchRead") {
                    "batchRead"
                } else {
                    "read"
                };
                serde_json::to_vec(&response_for_query(query_name)).unwrap()
            });
        Arc::new(runtime)
    }

    fn service_with_runtime(runtime: Arc<ServiceRuntime<AmsService>>) -> AmsService {
        let mut state = AmsState::load(runtime.root_view_storage_context())
            .blocking_wait()
            .expect("Failed to read from mock key value store");
        state.state_app_id.set(Some(state_application_id()));
        AmsService {
            runtime,
            state: Arc::new(state),
        }
    }

    fn test_metadata(application_id: ApplicationId, application_type: &str) -> Metadata {
        Metadata {
            creator: Account {
                chain_id: ChainId::from_str(
                    "aee928d4bf3880353b4a3cd9b6f88e6cc6e5ed050860abae439e7782e9b2dfe8",
                )
                .unwrap(),
                owner: AccountOwner::from_str(
                    "0x02e900512d2fca22897f80a2f6932ff454f2752ef7afad18729dd25e5b5b6e00",
                )
                .unwrap(),
            },
            application_name: "Test App".to_string(),
            application_id,
            application_type: application_type.to_string(),
            key_words: vec!["test".to_string()],
            logo_store_type: StoreType::S3,
            logo: CryptoHash::new(&TestString::new("logo".to_string())),
            description: "description".to_string(),
            twitter: None,
            telegram: None,
            discord: None,
            website: None,
            github: None,
            spec: None,
            created_at: Timestamp::from(1),
        }
    }

    fn ams_application_id() -> ApplicationId {
        application_id("a10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bad")
    }

    fn state_application_id() -> ApplicationId {
        application_id("b20ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bad")
    }

    fn application_id(value: &str) -> ApplicationId {
        ApplicationId::from_str(value).unwrap()
    }
}
