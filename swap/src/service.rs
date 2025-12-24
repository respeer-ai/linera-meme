#![cfg_attr(target_arch = "wasm32", no_main)]

use abi::swap::router::{Pool, SwapAbi};
use async_graphql::{EmptyMutation, EmptySubscription, Object, Request, Response, Schema};
use linera_sdk::{
    linera_base_types::ChainId, linera_base_types::WithServiceAbi, views::View, Service,
    ServiceRuntime,
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
    state: Arc<SwapState>,
    runtime: Arc<ServiceRuntime<SwapService>>,
}

#[Object]
impl QueryRoot {
    async fn pool_id(&self) -> &u64 {
        self.state.pool_id.get()
    }

    async fn pools(&self) -> Vec<Pool> {
        let mut pools: Vec<_> = self
            .state
            .meme_native_pools
            .index_values()
            .await
            .unwrap()
            .into_iter()
            .map(|(_, pool)| pool)
            .collect();
        for (_, _pools) in self.state.meme_meme_pools.index_values().await.unwrap() {
            pools.extend_from_slice(&_pools.into_values().collect::<Vec<Pool>>());
        }
        pools
    }

    async fn creator_chain_id(&self) -> ChainId {
        self.runtime.application_creator_chain_id()
    }
}

#[cfg(test)]
mod tests {
    #[test]
    fn query() {}
}
