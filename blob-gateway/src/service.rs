#![cfg_attr(target_arch = "wasm32", no_main)]

use abi::blob_gateway::{BlobData, BlobDataType, BlobGatewayAbi};
use async_graphql::{EmptyMutation, EmptySubscription, Object, Request, Response, Schema};
use blob_gateway::state::BlobGatewayState;
use linera_sdk::{
    linera_base_types::{CryptoHash, DataBlobHash, Timestamp, WithServiceAbi},
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
            EmptyMutation,
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

#[Object]
impl QueryRoot {
    async fn fetch(&self, blob_hash: DataBlobHash) -> Vec<u8> {
        self.runtime.lock().unwrap().read_data_blob(blob_hash)
    }

    async fn blobs(&self) -> Vec<BlobData> {
        let mut values: Vec<BlobData> = self
            .state
            .blobs
            .index_values()
            .await
            .expect("Failed get blobs")
            .into_iter()
            .map(|(_, v)| v)
            .collect::<Vec<_>>();
        values.sort_by(|a, b| a.created_at.cmp(&b.created_at));
        values
    }

    async fn blob(&self, blob_hash: CryptoHash) -> Option<BlobData> {
        self.state
            .blobs
            .get(&blob_hash)
            .await
            .expect("Failed get blob")
    }

    async fn list(
        &self,
        created_before: Option<Timestamp>,
        created_after: Option<Timestamp>,
        data_type: Option<BlobDataType>,
        limit: usize,
    ) -> Vec<BlobData> {
        let mut blobs: Vec<BlobData> = Vec::new();

        self.state
            .blobs
            .for_each_index_value_while(|_key, value| {
                if let Some(created_before) = created_before {
                    if value.created_at > created_before {
                        return Ok(true);
                    }
                }
                if let Some(created_after) = created_after {
                    if value.created_at < created_after {
                        return Ok(true);
                    }
                }
                if let Some(data_type) = data_type {
                    if data_type != value.data_type {
                        return Ok(true);
                    }
                }
                if limit > 0 && blobs.len() >= limit {
                    return Ok(false);
                }
                blobs.push(value.as_ref().clone());
                Ok(blobs.len() < limit)
            })
            .await
            .expect("Failed list blob");

        blobs.sort_by(|a, b| b.created_at.cmp(&a.created_at));

        blobs
    }
}
