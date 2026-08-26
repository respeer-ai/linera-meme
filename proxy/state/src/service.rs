#![cfg_attr(target_arch = "wasm32", no_main)]

use abi::proxy::state_v1::ProxyStateAbi;
use async_graphql::{EmptyMutation, EmptySubscription, Object, Request, Response, Schema};
use linera_sdk::{
    linera_base_types::{Account, ApplicationId, ChainId, ModuleId, Timestamp, WithServiceAbi},
    views::View,
    Service, ServiceRuntime,
};
use proxy_state::state::ProxyState;
use std::sync::Arc;

pub struct ProxyStateService {
    state: Arc<ProxyState>,
}

linera_sdk::service!(ProxyStateService);

impl WithServiceAbi for ProxyStateService {
    type Abi = ProxyStateAbi;
}

impl Service for ProxyStateService {
    type Parameters = ();

    async fn new(runtime: ServiceRuntime<Self>) -> Self {
        let state = ProxyState::load(runtime.root_view_storage_context())
            .await
            .expect("Failed to load proxy state v1");
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
    state: Arc<ProxyState>,
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

    async fn meme_bytecode_id(&self) -> ModuleId {
        self.state.meme_bytecode_id.get().unwrap()
    }

    async fn meme_state_bytecode_ids(&self) -> Vec<String> {
        let mut ids = self
            .state
            .meme_state_bytecode_ids
            .index_values()
            .await
            .expect("Failed to read meme state bytecode ids");
        ids.sort_by_key(|(version, _)| *version);
        ids.into_iter()
            .map(|(version, module_id)| format!("{}:{}", version, module_id))
            .collect()
    }

    async fn swap_application_id(&self) -> ApplicationId {
        self.state.swap_application_id.get().unwrap()
    }

    async fn is_genesis_miner(&self, owner: Account) -> bool {
        self.state
            .genesis_miners
            .contains_key(&owner)
            .await
            .expect("Failed to read genesis miners")
    }

    async fn miners(&self) -> Vec<abi::proxy::Miner> {
        self.state
            .miners
            .index_values()
            .await
            .expect("Failed to read miners")
            .into_iter()
            .map(|(_, miner)| miner)
            .collect()
    }

    async fn miner_owners(&self) -> Vec<linera_sdk::linera_base_types::AccountOwner> {
        self.state
            .miners
            .index_values()
            .await
            .expect("Failed to read miners")
            .into_iter()
            .map(|(_, miner)| miner.owner.owner)
            .collect()
    }

    async fn genesis_miners(&self) -> Vec<abi::proxy::Miner> {
        let mut miners = Vec::new();
        self.state
            .genesis_miners
            .for_each_index_value(|_, miner| {
                let miner = miner.into_owned();
                miners.push(abi::proxy::Miner {
                    owner: miner.owner,
                    registered_at: 0.into(),
                });
                Ok(())
            })
            .await
            .expect("Failed to read genesis miners");
        miners
    }

    async fn chain(&self, chain_id: ChainId) -> Option<abi::proxy::Chain> {
        self.state
            .chains
            .get(&chain_id)
            .await
            .expect("Failed to read chain")
    }

    async fn chains(&self, created_after: Option<Timestamp>) -> Vec<abi::proxy::Chain> {
        let mut chains = Vec::new();
        self.state
            .chains
            .for_each_index_value(|_, chain| {
                if created_after.map_or(true, |ts| chain.created_at >= ts) {
                    chains.push(chain.into_owned());
                }
                Ok(())
            })
            .await
            .expect("Failed to read chains");
        chains
    }

    async fn chain_by_token(
        &self,
        token: ApplicationId,
    ) -> Option<abi::proxy::Chain> {
        let mut found = None;
        self.state
            .chains
            .for_each_index_value(|_, chain| {
                if chain.token == Some(token) {
                    found = Some(chain.into_owned());
                }
                Ok(())
            })
            .await
            .expect("Failed to read chains");
        found
    }
}
