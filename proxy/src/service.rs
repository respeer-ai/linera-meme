// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

#![cfg_attr(target_arch = "wasm32", no_main)]

mod state;

use std::sync::Arc;

use abi::proxy::{Chain, ProxyAbi};
use async_graphql::{EmptyMutation, EmptySubscription, Object, Request, Response, Schema};
use linera_sdk::{
    linera_base_types::{Account, ApplicationId, ChainId, MessageId, ModuleId, WithServiceAbi},
    views::View,
    Service, ServiceRuntime,
};

use self::state::ProxyState;

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

#[Object]
impl QueryRoot {
    async fn meme_bytecode_id(&self) -> ModuleId {
        self.state.meme_bytecode_id.get().unwrap()
    }

    async fn genesis_miners(&self) -> Vec<Account> {
        self.state.genesis_miners().await.unwrap()
    }

    async fn miners(&self) -> Vec<Account> {
        self.state.miners().await.unwrap()
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

    async fn meme_chain_creation_messages(&self) -> Vec<MessageId> {
        self.state
            .chains
            .index_values()
            .await
            .unwrap()
            .into_iter()
            .map(|(_, chain)| chain.message_id)
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
mod tests {
    use std::sync::Arc;

    use async_graphql::{Request, Response, Value};
    use futures::FutureExt as _;
    use linera_sdk::{
        linera_base_types::ModuleId, util::BlockingWait, views::View, Service, ServiceRuntime,
    };
    use serde_json::json;
    use std::str::FromStr;

    use super::{ProxyService, ProxyState};

    #[test]
    fn query() {
        let meme_bytecode_id = ModuleId::from_str("b94e486abcfc016e937dad4297523060095f405530c95d498d981a94141589f167693295a14c3b48460ad6f75d67d2414428227550eb8cee8ecaa37e8646518300").unwrap();
        let runtime = Arc::new(ServiceRuntime::<ProxyService>::new());
        let mut state = ProxyState::load(runtime.root_view_storage_context())
            .blocking_wait()
            .expect("Failed to read from mock key value store");
        state.meme_bytecode_id.set(Some(meme_bytecode_id));

        let service = ProxyService {
            state: Arc::new(state),
            runtime,
        };
        let request = Request::new("{ memeBytecodeId }");

        let response = service
            .handle_query(request)
            .now_or_never()
            .expect("Query should not await anything");

        let expected =
            Response::new(Value::from_json(json!({"memeBytecodeId": meme_bytecode_id})).unwrap());

        assert_eq!(response, expected)
    }
}
