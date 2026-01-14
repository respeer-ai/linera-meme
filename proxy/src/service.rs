// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

#![cfg_attr(target_arch = "wasm32", no_main)]

use std::sync::Arc;

use abi::proxy::{Chain, ProxyAbi};
use async_graphql::{EmptyMutation, EmptySubscription, Object, Request, Response, Schema};
use linera_sdk::{
    linera_base_types::{Account, AccountOwner, ApplicationId, ChainId, ModuleId, WithServiceAbi},
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
            EmptyMutation,
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
    async fn _genesis_miners(&self) -> Vec<Account> {
        let mut miners = Vec::new();
        self.state
            .genesis_miners
            .for_each_index_value(|owner, miner| {
                let approval = miner.into_owned().approval;
                if approval.approved() {
                    miners.push(owner);
                }
                Ok(())
            })
            .await
            .expect("Failed: genesis miners");
        miners
    }

    async fn _miners(&self) -> Vec<Account> {
        self.state
            .miners
            .indices()
            .await
            .expect("Failed: miners")
            .iter()
            .chain(self._genesis_miners().await.iter())
            .cloned()
            .collect()
    }
}

#[Object]
impl QueryRoot {
    async fn meme_bytecode_id(&self) -> ModuleId {
        self.state.meme_bytecode_id.get().unwrap()
    }

    async fn genesis_miners(&self) -> Vec<Account> {
        self._genesis_miners().await
    }

    async fn miners(&self) -> Vec<Account> {
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

    async fn meme_chains(&self) -> Vec<Chain> {
        self.state
            .chains
            .index_values()
            .await
            .unwrap()
            .into_iter()
            .map(|(_, chain)| chain)
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

#[cfg(test)]
mod service_tests;
