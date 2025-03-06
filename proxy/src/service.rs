// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

#![cfg_attr(target_arch = "wasm32", no_main)]

mod state;

use std::sync::Arc;

use abi::proxy::{Chain, ProxyAbi, ProxyOperation};
use async_graphql::{EmptySubscription, Object, Request, Response, Schema};
use linera_sdk::{
    linera_base_types::{ApplicationId, MessageId, ModuleId, Owner, WithServiceAbi},
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

struct MutationRoot {
    runtime: Arc<ServiceRuntime<ProxyService>>,
}

#[Object]
impl MutationRoot {
    async fn propose_add_genesis_miner(&self, owner: Owner, endpoint: Option<String>) -> [u8; 0] {
        self.runtime
            .schedule_operation(&ProxyOperation::ProposeAddGenesisMiner { owner, endpoint });
        []
    }
}

struct QueryRoot {
    state: Arc<ProxyState>,
}

#[Object]
impl QueryRoot {
    async fn meme_bytecode_id(&self) -> ModuleId {
        self.state.meme_bytecode_id.get().unwrap()
    }

    async fn genesis_miners(&self) -> Vec<Owner> {
        self.state.genesis_miners().await.unwrap()
    }

    async fn count_meme_chains(&self) -> usize {
        self.state.chains.count().await.unwrap()
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

    async fn meme_applications(&self) -> Vec<Option<ApplicationId>> {
        self.state
            .chains
            .index_values()
            .await
            .unwrap()
            .into_iter()
            .map(|(_, chain)| chain.token)
            .collect()
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
