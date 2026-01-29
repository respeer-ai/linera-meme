// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

#![cfg_attr(target_arch = "wasm32", no_main)]

use std::sync::Arc;

use abi::proxy::{Chain, Miner, ProxyAbi, ProxyOperation};
use async_graphql::{EmptySubscription, Object, Request, Response, Schema};
use linera_sdk::{
    linera_base_types::{
        AccountOwner, ApplicationId, ChainId, ModuleId, Timestamp, WithServiceAbi,
    },
    views::View,
    Service, ServiceRuntime,
};

use proxy::state::ProxyState;

pub struct ProxyService {
    state: Arc<ProxyState>,
    runtime: Arc<ServiceRuntime<Self>>,
}

linera_sdk::service!(ProxyService);

impl WithServiceAbi for ProxyService {
    type Abi = ProxyAbi;
}

impl Service for ProxyService {
    type Parameters = ();

    async fn new(runtime: ServiceRuntime<Self>) -> Self {
        let state = ProxyState::load(runtime.root_view_storage_context())
            .await
            .expect("Failed to load state");
        ProxyService {
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
    state: Arc<ProxyState>,
    runtime: Arc<ServiceRuntime<ProxyService>>,
}

impl QueryRoot {
    async fn _genesis_miners(&self) -> Vec<Miner> {
        let mut miners = Vec::new();
        self.state
            .genesis_miners
            .for_each_index_value(|owner, miner| {
                let approval = miner.into_owned().approval;
                if approval.approved() {
                    miners.push(Miner {
                        owner,
                        registered_at: 0.into(),
                    });
                }
                Ok(())
            })
            .await
            .expect("Failed get genesis miner");
        miners
    }

    async fn _miners(&self) -> Vec<Miner> {
        let genesis_miners = self._genesis_miners().await;

        self.state
            .miners
            .index_values()
            .await
            .expect("Failed get miner")
            .into_iter()
            .map(|(_, miner)| miner)
            .chain(genesis_miners.into_iter())
            .collect()
    }

    async fn _miner(&self, owner: AccountOwner) -> Option<Miner> {
        self._miners()
            .await
            .into_iter()
            .find(|miner| miner.owner.owner == owner)
    }
}

#[Object]
impl QueryRoot {
    async fn meme_bytecode_id(&self) -> ModuleId {
        self.state.meme_bytecode_id.get().unwrap()
    }

    async fn genesis_miners(&self) -> Vec<Miner> {
        self._genesis_miners().await
    }

    async fn miners(&self) -> Vec<Miner> {
        self._miners().await
    }

    async fn miner_registered(&self, owner: AccountOwner) -> bool {
        self.state
            .miners
            .indices()
            .await
            .expect("Failed check miner")
            .iter()
            .any(|_owner| _owner.owner == owner)
            || self
                .state
                .genesis_miners
                .indices()
                .await
                .expect("Failed check genesis miner")
                .iter()
                .any(|_owner| _owner.owner == owner)
    }

    async fn miner(&self, owner: AccountOwner) -> Option<Miner> {
        self._miner(owner).await
    }

    async fn meme_chains(&self, created_after: Option<Timestamp>) -> Vec<Chain> {
        let created_after = created_after.unwrap_or(0.into());

        self.state
            .chains
            .index_values()
            .await
            .unwrap()
            .into_iter()
            .filter_map(|(_, chain)| (chain.created_at > created_after).then_some(chain))
            .collect()
    }

    async fn meme_applications(&self) -> Vec<Chain> {
        self.state
            .chains
            .index_values()
            .await
            .unwrap()
            .into_iter()
            .map(|(_, chain)| chain)
            .collect::<Vec<_>>()
            .into_iter()
            .filter(|chain| chain.token.is_some())
            .collect()
    }

    async fn meme_application_ids(&self) -> Vec<Option<ApplicationId>> {
        self.state
            .chains
            .index_values()
            .await
            .unwrap()
            .into_iter()
            .map(|(_, chain)| chain.token)
            .collect()
    }

    async fn creator_chain_id(&self) -> ChainId {
        self.runtime.application_creator_chain_id()
    }
}

struct MutationRoot {
    runtime: Arc<ServiceRuntime<ProxyService>>,
}

#[Object]
impl MutationRoot {
    async fn register_miner(&self) -> [u8; 0] {
        self.runtime
            .schedule_operation(&ProxyOperation::RegisterMiner);
        []
    }
}

#[cfg(test)]
mod service_tests;
