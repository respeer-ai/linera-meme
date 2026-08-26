// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

#![cfg_attr(target_arch = "wasm32", no_main)]

use std::sync::Arc;

use abi::{
    meme::{InstantiationArgument as MemeInstantiationArgument, MemeParameters},
    proxy::{Chain, Miner, ProxyAbi, ProxyOperation},
};
use async_graphql::{EmptySubscription, Object, Request, Response, Schema};
use linera_sdk::{
    linera_base_types::{
        AccountOwner, ApplicationId, ChainId, ModuleId, Timestamp, WithServiceAbi,
    },
    views::View,
    Service, ServiceRuntime,
};

use proxy::state::{adapter::ServiceStateAdapter, ProxyState};

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
    fn state_adapter(&self) -> ServiceStateAdapter<ProxyService> {
        ServiceStateAdapter::new(self.runtime.clone(), self.state.clone())
            .expect("Failed to create state adapter")
    }

    async fn _genesis_miners(&self) -> Vec<Miner> {
        self.state_adapter()
            .genesis_miners()
            .await
            .expect("Failed get genesis miner")
    }

    async fn _miners(&self) -> Vec<Miner> {
        self.state_adapter()
            .miners()
            .await
            .expect("Failed get miner")
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
        self.state_adapter()
            .meme_bytecode_id()
            .await
            .expect("Failed get meme bytecode id")
    }

    async fn genesis_miners(&self) -> Vec<Miner> {
        self._genesis_miners().await
    }

    async fn miners(&self) -> Vec<Miner> {
        self._miners().await
    }

    async fn miner_registered(&self, owner: AccountOwner) -> bool {
        let adapter = self.state_adapter();
        adapter
            .miner_owners()
            .await
            .expect("Failed check miner")
            .iter()
            .any(|_owner| *_owner == owner)
    }

    async fn miner(&self, owner: AccountOwner) -> Option<Miner> {
        self._miner(owner).await
    }

    async fn meme_chains(&self, created_after: Option<Timestamp>) -> Vec<Chain> {
        let created_after = created_after.unwrap_or(0.into());

        self.state_adapter()
            .chains(Some(created_after))
            .await
            .expect("Failed get meme chains")
            .into_iter()
            .filter(|chain| chain.created_at > created_after)
            .collect()
    }

    async fn meme_chain(&self, token: ApplicationId) -> Option<Chain> {
        self.state_adapter()
            .chain_by_token(token)
            .await
            .expect("Failed get meme chain")
    }

    async fn meme_applications(&self) -> Vec<Chain> {
        self.state_adapter()
            .chains(None)
            .await
            .expect("Failed get meme applications")
            .into_iter()
            .filter(|chain| chain.token.is_some())
            .collect()
    }

    async fn meme_application_ids(&self) -> Vec<Option<ApplicationId>> {
        self.state_adapter()
            .chains(None)
            .await
            .expect("Failed get meme application ids")
            .into_iter()
            .map(|chain| chain.token)
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

    async fn create_meme(
        &self,
        meme_instantiation_argument: MemeInstantiationArgument,
        meme_parameters: MemeParameters,
    ) -> [u8; 0] {
        // Mutation should always be from other chain.
        assert!(
            self.runtime.application_creator_chain_id() != self.runtime.chain_id(),
            "Permission denied"
        );

        self.runtime
            .schedule_operation(&ProxyOperation::CreateMeme {
                meme_instantiation_argument,
                meme_parameters,
            });
        []
    }
}

#[cfg(test)]
mod service_tests;
