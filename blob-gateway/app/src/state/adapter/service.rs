use std::sync::Arc;

use crate::state::BlobGatewayState;
use abi::{
    application_state_base::{decode_response_field, LocalStateInterface},
    blob_gateway::{
        state_v1::BlobGatewayStateAbi as BlobGatewayStateV1Abi, BlobData, BlobDataType,
    },
};
use async_graphql::{Request, Variables};
use linera_sdk::{linera_base_types::CryptoHash, serde_json::json, Service, ServiceRuntime};

use super::StateError;

enum BlobGatewayStateQuery {
    Blob {
        blob_hash: CryptoHash,
    },
    Blobs,
    List {
        created_before: Option<linera_sdk::linera_base_types::Timestamp>,
        created_after: Option<linera_sdk::linera_base_types::Timestamp>,
        data_type: Option<BlobDataType>,
        limit: usize,
    },
}

impl BlobGatewayStateQuery {
    const BLOB_FIELD: &'static str = "blob";
    const BLOBS_FIELD: &'static str = "blobs";
    const LIST_FIELD: &'static str = "list";

    fn request(&self) -> Request {
        match self {
            Self::Blob { blob_hash } => Request::new(
                "query($blobHash: CryptoHash!) { blob(blobHash: $blobHash) { storeType dataType blobHash creator createdAt } }",
            )
            .variables(Variables::from_json(json!({
                "blobHash": blob_hash,
            }))),
            Self::Blobs => Request::new(
                "query { blobs { storeType dataType blobHash creator createdAt } }",
            ),
            Self::List {
                created_before,
                created_after,
                data_type,
                limit,
            } => Request::new(
                "query($createdBefore: Timestamp, $createdAfter: Timestamp, $dataType: BlobDataType, $limit: Int!) { list(createdBefore: $createdBefore, createdAfter: $createdAfter, dataType: $dataType, limit: $limit) { storeType dataType blobHash creator createdAt } }",
            )
            .variables(Variables::from_json(json!({
                "createdBefore": created_before,
                "createdAfter": created_after,
                "dataType": data_type,
                "limit": limit,
            }))),
        }
    }
}

pub struct ServiceStateAdapter<S: Service> {
    runtime: Arc<std::sync::Mutex<ServiceRuntime<S>>>,
    state: Arc<BlobGatewayState>,
}

impl<S: Service> ServiceStateAdapter<S> {
    pub fn new(
        runtime: Arc<std::sync::Mutex<ServiceRuntime<S>>>,
        state: Arc<BlobGatewayState>,
    ) -> Result<Self, StateError> {
        Ok(Self { runtime, state })
    }

    pub async fn blob(&self, blob_hash: CryptoHash) -> Result<Option<BlobData>, StateError> {
        let query = BlobGatewayStateQuery::Blob { blob_hash };
        let state_application_id = self.state.latest_state_application().await?;
        let response = self.runtime.lock().unwrap().query_application(
            state_application_id.with_abi::<BlobGatewayStateV1Abi>(),
            &query.request(),
        );
        Ok(decode_response_field(
            response,
            BlobGatewayStateQuery::BLOB_FIELD,
        )?)
    }

    pub async fn blobs(&self) -> Result<Vec<BlobData>, StateError> {
        let query = BlobGatewayStateQuery::Blobs;
        let state_application_id = self.state.latest_state_application().await?;
        let response = self.runtime.lock().unwrap().query_application(
            state_application_id.with_abi::<BlobGatewayStateV1Abi>(),
            &query.request(),
        );
        Ok(decode_response_field(
            response,
            BlobGatewayStateQuery::BLOBS_FIELD,
        )?)
    }

    pub async fn list(
        &self,
        created_before: Option<linera_sdk::linera_base_types::Timestamp>,
        created_after: Option<linera_sdk::linera_base_types::Timestamp>,
        data_type: Option<BlobDataType>,
        limit: usize,
    ) -> Result<Vec<BlobData>, StateError> {
        let query = BlobGatewayStateQuery::List {
            created_before,
            created_after,
            data_type,
            limit,
        };
        let state_application_id = self.state.latest_state_application().await?;
        let response = self.runtime.lock().unwrap().query_application(
            state_application_id.with_abi::<BlobGatewayStateV1Abi>(),
            &query.request(),
        );
        Ok(decode_response_field(
            response,
            BlobGatewayStateQuery::LIST_FIELD,
        )?)
    }
}
