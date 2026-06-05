#![cfg_attr(target_arch = "wasm32", no_main)]

use abi::swap::router::{Pool, SwapAbi, SwapOperation};
use async_graphql::{EmptySubscription, Object, Request, Response, Schema};
use linera_sdk::{
    linera_base_types::WithServiceAbi,
    linera_base_types::{Account, Amount, ApplicationId, ChainId},
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

struct MutationRoot {
    runtime: Arc<ServiceRuntime<SwapService>>,
}

#[Object]
impl MutationRoot {
    async fn create_pool(
        &self,
        token_0: ApplicationId,
        token_1: Option<ApplicationId>,
        amount_0: Amount,
        amount_1: Amount,
        to: Option<Account>,
    ) -> [u8; 0] {
        assert!(
            self.runtime.application_creator_chain_id() != self.runtime.chain_id(),
            "Permission denied"
        );

        self.runtime.schedule_operation(&SwapOperation::CreatePool {
            token_0,
            token_1,
            amount_0,
            amount_1,
            to,
        });
        []
    }
}

#[cfg(test)]
mod tests {
    use super::SwapService;
    use abi::swap::router::Pool;
    use async_graphql::Request;
    use linera_sdk::{
        linera_base_types::{Account, AccountOwner, ApplicationId, ChainId},
        views::View,
        Service, ServiceRuntime,
    };
    use serde_json::json;
    use std::{collections::HashMap, str::FromStr, sync::Arc};
    use swap::state::SwapState;

    #[test]
    fn query() {}

    #[tokio::test]
    async fn pools_query_exposes_protocol_catalog_entries_before_finalized_reserves() {
        let runtime = Arc::new(ServiceRuntime::<SwapService>::new());
        let mut state = SwapState::load(runtime.root_view_storage_context())
            .await
            .expect("Failed to load swap state");
        let token_0 = ApplicationId::from_str(
            "b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bad",
        )
        .unwrap();
        let token_1 = ApplicationId::from_str(
            "b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bae",
        )
        .unwrap();
        let creator = Account {
            chain_id: ChainId::from_str(
                "aee928d4bf3880353b4a3cd9b6f88e6cc6e5ed050860abae439e7782e9b2dfe8",
            )
            .unwrap(),
            owner: AccountOwner::from_str(
                "0x5279b3ae14d3b38e14b65a74aefe44824ea88b25c7841836e9ec77d991a5bc7f",
            )
            .unwrap(),
        };
        let pool_application = Account {
            chain_id: ChainId::from_str(
                "bee928d4bf3880353b4a3cd9b6f88e6cc6e5ed050860abae439e7782e9b2dfe8",
            )
            .unwrap(),
            owner: AccountOwner::from(
                ApplicationId::from_str(
                    "b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bb0",
                )
                .unwrap(),
            ),
        };

        state
            .meme_meme_pools
            .insert(
                &token_0,
                HashMap::from([(
                    token_1,
                    Pool {
                        creator,
                        pool_id: 1000,
                        token_0,
                        token_1: Some(token_1),
                        pool_application,
                        token_0_price: None,
                        token_1_price: None,
                        reserve_0: None,
                        reserve_1: None,
                        created_at: 1.into(),
                    },
                )]),
            )
            .unwrap();

        let service = SwapService {
            state: Arc::new(state),
            runtime,
        };
        let response = service
            .handle_query(Request::new(
                "query { pools { poolId token0 token1 poolApplication token0Price token1Price reserve0 reserve1 } }",
            ))
            .await;

        assert!(response.errors.is_empty(), "{:?}", response.errors);
        let data = response.data.into_json().unwrap();
        assert_eq!(data["pools"].as_array().unwrap().len(), 1);
        assert_eq!(data["pools"][0]["poolId"], json!(1000));
        assert_eq!(data["pools"][0]["reserve0"], json!(null));
        assert_eq!(data["pools"][0]["reserve1"], json!(null));
        assert_eq!(data["pools"][0]["token0Price"], json!(null));
        assert_eq!(data["pools"][0]["token1Price"], json!(null));
    }
}
