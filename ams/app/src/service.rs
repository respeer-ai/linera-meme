#![cfg_attr(target_arch = "wasm32", no_main)]

use abi::ams::abi::{AmsAbi, AmsOperation, Metadata};
use ams_app::state::{adapter::ServiceStateAdapter, AmsState};
use async_graphql::{EmptySubscription, Object, Request, Response, Schema, SimpleObject};
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
            MutationRoot {
                runtime: self.runtime.clone(),
            },
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
            .await
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
            .await
            .expect("Failed to read AMS application from state")
    }

    async fn latest_state_version(&self) -> u16 {
        *self.state.latest_state_version.get()
    }

    async fn state_applications(&self) -> Vec<StateApplicationEntry> {
        self.state
            .state_applications
            .index_values()
            .await
            .expect("Failed to read state applications from state")
            .into_iter()
            .map(|(version, application_id)| StateApplicationEntry {
                version,
                application_id,
            })
            .collect()
    }
}

#[derive(SimpleObject)]
struct StateApplicationEntry {
    version: u16,
    application_id: ApplicationId,
}

struct MutationRoot {
    runtime: Arc<ServiceRuntime<AmsService>>,
}

#[Object]
impl MutationRoot {
    async fn append_state(&self, state_application_id: ApplicationId) -> bool {
        self.runtime.schedule_operation(&AmsOperation::AppendState {
            state_application_id,
        });
        true
    }

    async fn handoff(&self, new_business_application_id: ApplicationId) -> bool {
        self.runtime.schedule_operation(&AmsOperation::Handoff {
            new_business_application_id,
        });
        true
    }
}

impl QueryRoot {
    fn state_adapter(
        &self,
    ) -> Result<ServiceStateAdapter<AmsService>, ams_app::state::errors::StateError> {
        ServiceStateAdapter::new(self.runtime.clone(), self.state.clone())
    }
}

#[cfg(test)]
mod service_tests {
    use super::*;
    use abi::store_type::StoreType;
    use async_graphql::Value;
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
            assert_eq!(query, "application");
            Response::new(
                Value::from_json(json!({
                    "application": metadata_for_query.clone(),
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
                    assert_eq!(query, "applications");
                    Response::new(
                        Value::from_json(json!({
                            "applications": vec![metadata_for_query.clone()],
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

    #[tokio::test(flavor = "multi_thread")]
    async fn latest_state_version_query_reads_state_register() {
        let runtime = runtime();
        let service = service_with_runtime(runtime);

        let response = service
            .handle_query(Request::new("{ latestStateVersion }"))
            .await;

        let expected = Response::new(Value::from_json(json!({ "latestStateVersion": 1 })).unwrap());
        assert_eq!(response, expected);
    }

    #[tokio::test(flavor = "multi_thread")]
    async fn state_applications_query_reads_state_index() {
        let runtime = runtime();
        let service = service_with_runtime(runtime);

        let response = service
            .handle_query(Request::new(
                "{ stateApplications { version applicationId } }",
            ))
            .await;

        let expected = Response::new(
            Value::from_json(json!({
                "stateApplications": [{
                    "version": 1,
                    "applicationId": state_application_id(),
                }],
            }))
            .unwrap(),
        );
        assert_eq!(response, expected);
    }

    #[tokio::test(flavor = "multi_thread")]
    async fn append_state_mutation_schedules_operation() {
        let new_state_id =
            application_id("c30ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bae");
        let runtime = runtime();
        let service = service_with_runtime(runtime.clone());

        let response = service
            .handle_query(Request::new(format!(
                "mutation {{ appendState(stateApplicationId: \"{}\") }}",
                new_state_id
            )))
            .await;

        let expected = Response::new(Value::from_json(json!({ "appendState": true })).unwrap());
        assert_eq!(response, expected);

        let operations: Vec<AmsOperation> = runtime.scheduled_operations();
        assert_eq!(operations.len(), 1);
        assert!(
            matches!(
                &operations[0],
                AmsOperation::AppendState {
                    state_application_id,
                } if *state_application_id == new_state_id
            ),
            "unexpected scheduled operation: {:?}",
            operations[0]
        );
    }

    #[tokio::test(flavor = "multi_thread")]
    async fn handoff_mutation_schedules_operation() {
        let new_business_id =
            application_id("c40ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bae");
        let runtime = runtime();
        let service = service_with_runtime(runtime.clone());

        let response = service
            .handle_query(Request::new(format!(
                "mutation {{ handoff(newBusinessApplicationId: \"{}\") }}",
                new_business_id
            )))
            .await;

        let expected = Response::new(Value::from_json(json!({ "handoff": true })).unwrap());
        assert_eq!(response, expected);

        let operations: Vec<AmsOperation> = runtime.scheduled_operations();
        assert_eq!(operations.len(), 1);
        assert!(
            matches!(
                &operations[0],
                AmsOperation::Handoff {
                    new_business_application_id,
                } if *new_business_application_id == new_business_id
            ),
            "unexpected scheduled operation: {:?}",
            operations[0]
        );
    }

    fn runtime() -> Arc<ServiceRuntime<AmsService>> {
        Arc::new(
            ServiceRuntime::<AmsService>::new()
                .with_application_id(ams_application_id().with_abi::<AmsAbi>()),
        )
    }

    fn runtime_with_state_query(
        mut response_for_query: impl FnMut(&str) -> Response + Send + 'static,
    ) -> Arc<ServiceRuntime<AmsService>> {
        let runtime = ServiceRuntime::<AmsService>::new()
            .with_application_id(ams_application_id().with_abi::<AmsAbi>())
            .with_query_application_handler(move |application_id, query| {
                assert_eq!(application_id, state_application_id());
                let request: Request = serde_json::from_slice(&query).unwrap();
                let query_name = if request.query.contains("applications") {
                    "applications"
                } else {
                    "application"
                };
                serde_json::to_vec(&response_for_query(query_name)).unwrap()
            });
        Arc::new(runtime)
    }

    fn service_with_runtime(runtime: Arc<ServiceRuntime<AmsService>>) -> AmsService {
        let mut state = AmsState::load(runtime.root_view_storage_context())
            .blocking_wait()
            .expect("Failed to read from mock key value store");
        state
            .state_applications
            .insert(&1, state_application_id())
            .expect("Failed to set state application");
        state.latest_state_version.set(1);
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
