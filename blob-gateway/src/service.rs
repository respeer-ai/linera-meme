#![cfg_attr(target_arch = "wasm32", no_main)]

use abi::blob_gateway::{BlobData, BlobGatewayAbi};
use async_graphql::{EmptyMutation, EmptySubscription, Object, Request, Response, Schema};
use blob_gateway::state::BlobGatewayState;
use linera_sdk::{
    graphql::GraphQLMutationRoot,
    linera_base_types::{CryptoHash, WithServiceAbi},
    views::View,
    Service, ServiceRuntime,
};
use std::sync::Arc;

pub struct BlobGatewayService {
    state: Arc<BlobGatewayState>,
    runtime: Arc<ServiceRuntime<Self>>,
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
            runtime: Arc::new(runtime),
        }
    }

    async fn handle_query(&self, request: Request) -> Response {
        let schema = Schema::build(
            QueryRoot {
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
    state: Arc<BlobGatewayState>,
}

#[Object]
impl QueryRoot {
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
}
