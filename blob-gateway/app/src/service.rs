#![cfg_attr(target_arch = "wasm32", no_main)]

use abi::blob_gateway::{BlobData, BlobDataType, BlobGatewayAbi, BlobGatewayOperation};
use async_graphql::{EmptySubscription, Object, Request, Response, Schema, SimpleObject};
use blob_gateway_app::state::{adapter::ServiceStateAdapter, BlobGatewayState};
use linera_sdk::{
    linera_base_types::{ApplicationId, CryptoHash, DataBlobHash, Timestamp, WithServiceAbi},
    views::View,
    Service, ServiceRuntime,
};
use std::sync::{Arc, Mutex};

pub struct BlobGatewayService {
    state: Arc<BlobGatewayState>,
    runtime: Arc<Mutex<ServiceRuntime<BlobGatewayService>>>,
}

linera_sdk::service!(BlobGatewayService);

impl WithServiceAbi for BlobGatewayService {
    type Abi = BlobGatewayAbi;
}

impl Service for BlobGatewayService {
    type Parameters = ();

    async fn new(runtime: ServiceRuntime<Self>) -> Self {
        let state = BlobGatewayState::load(runtime.root_view_storage_context())
            .await
            .expect("Failed to load state");
        BlobGatewayService {
            state: Arc::new(state),
            runtime: Arc::new(Mutex::new(runtime)),
        }
    }

    async fn handle_query(&self, request: Request) -> Response {
        let schema = Schema::build(
            QueryRoot {
                state: self.state.clone(),
                runtime: self.runtime.clone(),
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
    state: Arc<BlobGatewayState>,
    runtime: Arc<Mutex<ServiceRuntime<BlobGatewayService>>>,
}

#[derive(SimpleObject)]
struct StateApplicationEntry {
    version: u16,
    application_id: ApplicationId,
}

#[Object]
impl QueryRoot {
    async fn fetch(&self, blob_hash: DataBlobHash) -> Vec<u8> {
        self.runtime.lock().unwrap().read_data_blob(blob_hash)
    }

    async fn blobs(&self) -> Vec<BlobData> {
        self.state_adapter()
            .expect("Failed to create service state adapter")
            .blobs()
            .await
            .expect("Failed to read blobs from state")
    }

    async fn blob(&self, blob_hash: CryptoHash) -> Option<BlobData> {
        self.state_adapter()
            .expect("Failed to create service state adapter")
            .blob(blob_hash)
            .await
            .expect("Failed to read blob from state")
    }

    async fn list(
        &self,
        created_before: Option<Timestamp>,
        created_after: Option<Timestamp>,
        data_type: Option<BlobDataType>,
        limit: usize,
    ) -> Vec<BlobData> {
        self.state_adapter()
            .expect("Failed to create service state adapter")
            .list(created_before, created_after, data_type, limit)
            .await
            .expect("Failed to list blobs from state")
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

impl QueryRoot {
    fn state_adapter(
        &self,
    ) -> Result<ServiceStateAdapter<BlobGatewayService>, blob_gateway_app::state::errors::StateError>
    {
        ServiceStateAdapter::new(self.runtime.clone(), self.state.clone())
    }
}

struct MutationRoot {
    runtime: Arc<Mutex<ServiceRuntime<BlobGatewayService>>>,
}

#[Object]
impl MutationRoot {
    async fn append_state(&self, state_application_id: ApplicationId) -> bool {
        self.runtime
            .lock()
            .unwrap()
            .schedule_operation(&BlobGatewayOperation::AppendState {
                state_application_id,
            });
        true
    }

    async fn handoff(&self, new_business_application_id: ApplicationId) -> bool {
        self.runtime
            .lock()
            .unwrap()
            .schedule_operation(&BlobGatewayOperation::Handoff {
                new_business_application_id,
            });
        true
    }
}

#[cfg(test)]
mod service_tests {
    use super::*;
    use abi::{blob_gateway::BlobGatewayOperation, store_type::StoreType};
    use async_graphql::{Request, Value};
    use linera_sdk::{
        linera_base_types::{
            Account, AccountOwner, ApplicationId, ChainId, CryptoHash, TestString, Timestamp,
        },
        util::BlockingWait,
    };
    use serde_json::json;
    use std::str::FromStr;

    #[tokio::test(flavor = "multi_thread")]
    async fn blobs_query_reads_state_application() {
        let blob_data = test_blob_data();
        let blob_data_for_query = blob_data.clone();
        let runtime = runtime_with_state_query(move |query| {
            assert!(query.contains("blobs"));
            Response::new(
                Value::from_json(json!({
                    "blobs": vec![blob_data_for_query.clone()],
                }))
                .unwrap(),
            )
        });
        let service = service_with_runtime(runtime);

        let response = service
            .handle_query(Request::new("{ blobs { blobHash } }"))
            .await;

        let expected = Response::new(
            Value::from_json(json!({ "blobs": [{ "blobHash": blob_data.blob_hash }] })).unwrap(),
        );
        assert_eq!(response, expected);
    }

    #[tokio::test(flavor = "multi_thread")]
    async fn blob_query_reads_state_application() {
        let blob_data = test_blob_data();
        let blob_hash = blob_data.blob_hash;
        let blob_data_for_query = blob_data.clone();
        let runtime = runtime_with_state_query(move |query| {
            assert!(query.contains("blob"));
            Response::new(
                Value::from_json(json!({
                    "blob": blob_data_for_query.clone(),
                }))
                .unwrap(),
            )
        });
        let service = service_with_runtime(runtime);

        let response = service
            .handle_query(Request::new(format!(
                "{{ blob(blobHash: \"{}\") {{ blobHash }} }}",
                blob_hash
            )))
            .await;

        let expected =
            Response::new(Value::from_json(json!({ "blob": { "blobHash": blob_hash } })).unwrap());
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
        let new_state_id = state_application_id();
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

        let operations: Vec<BlobGatewayOperation> = runtime.lock().unwrap().scheduled_operations();
        assert_eq!(operations.len(), 1);
        assert!(
            matches!(
                &operations[0],
                BlobGatewayOperation::AppendState { state_application_id } if state_application_id == &new_state_id
            ),
            "unexpected scheduled operation: {:?}",
            operations[0]
        );
    }

    #[tokio::test(flavor = "multi_thread")]
    async fn handoff_mutation_schedules_operation() {
        let new_business_id = other_application_id();
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

        let operations: Vec<BlobGatewayOperation> = runtime.lock().unwrap().scheduled_operations();
        assert_eq!(operations.len(), 1);
        assert!(
            matches!(
                &operations[0],
                BlobGatewayOperation::Handoff { new_business_application_id } if new_business_application_id == &new_business_id
            ),
            "unexpected scheduled operation: {:?}",
            operations[0]
        );
    }

    fn runtime() -> Arc<Mutex<ServiceRuntime<BlobGatewayService>>> {
        Arc::new(Mutex::new(
            ServiceRuntime::<BlobGatewayService>::new()
                .with_application_id(blob_gateway_application_id().with_abi::<BlobGatewayAbi>()),
        ))
    }

    fn runtime_with_state_query(
        mut response_for_query: impl FnMut(&str) -> Response + Send + 'static,
    ) -> Arc<Mutex<ServiceRuntime<BlobGatewayService>>> {
        let runtime = ServiceRuntime::<BlobGatewayService>::new()
            .with_application_id(blob_gateway_application_id().with_abi::<BlobGatewayAbi>())
            .with_query_application_handler(move |application_id, query| {
                assert_eq!(application_id, state_application_id());
                let request: Request = serde_json::from_slice(&query).unwrap();
                let query_name = if request.query.contains("blobs {") {
                    "blobs"
                } else {
                    "blob"
                };
                serde_json::to_vec(&response_for_query(query_name)).unwrap()
            });
        Arc::new(Mutex::new(runtime))
    }

    fn service_with_runtime(
        runtime: Arc<Mutex<ServiceRuntime<BlobGatewayService>>>,
    ) -> BlobGatewayService {
        let mut state = BlobGatewayState::load(runtime.lock().unwrap().root_view_storage_context())
            .blocking_wait()
            .expect("Failed to read from mock key value store");
        state
            .state_applications
            .insert(&1, state_application_id())
            .expect("Failed to set state application");
        state.latest_state_version.set(1);
        BlobGatewayService {
            runtime,
            state: Arc::new(state),
        }
    }

    fn test_blob_data() -> BlobData {
        BlobData {
            store_type: StoreType::S3,
            data_type: BlobDataType::Image,
            blob_hash: CryptoHash::new(&TestString::new("logo".to_string())),
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
            created_at: Timestamp::from(1),
        }
    }

    fn blob_gateway_application_id() -> ApplicationId {
        application_id("b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bad")
    }

    fn state_application_id() -> ApplicationId {
        application_id("b20ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bad")
    }

    fn other_application_id() -> ApplicationId {
        application_id("b30ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bad")
    }

    fn application_id(value: &str) -> ApplicationId {
        ApplicationId::from_str(value).unwrap()
    }
}
