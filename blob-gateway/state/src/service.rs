#![cfg_attr(target_arch = "wasm32", no_main)]

use abi::blob_gateway::{state_v1::BlobGatewayStateAbi, BlobData, BlobDataType};
use async_graphql::{EmptyMutation, EmptySubscription, Object, Request, Response, Schema};
use blob_gateway_state::state::BlobGatewayStateV1;
use linera_sdk::{
    linera_base_types::{
        Account, ApplicationId, CryptoHash, DataBlobHash, Timestamp, WithServiceAbi,
    },
    views::View,
    Service, ServiceRuntime,
};
use std::sync::Arc;

pub struct BlobGatewayStateService {
    state: Arc<BlobGatewayStateV1>,
}

linera_sdk::service!(BlobGatewayStateService);

impl WithServiceAbi for BlobGatewayStateService {
    type Abi = BlobGatewayStateAbi;
}

impl Service for BlobGatewayStateService {
    type Parameters = ();

    async fn new(runtime: ServiceRuntime<Self>) -> Self {
        let state = BlobGatewayStateV1::load(runtime.root_view_storage_context())
            .await
            .expect("Failed to load blob gateway StateV1 state");
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
    state: Arc<BlobGatewayStateV1>,
}

#[Object]
impl QueryRoot {
    async fn health(&self) -> bool {
        true
    }

    async fn business_application_id(&self) -> Option<ApplicationId> {
        *self.state.business_application_id.get()
    }

    async fn operator(&self) -> Option<Account> {
        *self.state.operator.get()
    }

    async fn fetch(&self, _blob_hash: DataBlobHash) -> Vec<u8> {
        // The state service does not have direct access to the data blob runtime.
        // Fetching raw blob bytes is a business-app concern.
        Vec::new()
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
