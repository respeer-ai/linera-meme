// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

#![cfg_attr(target_arch = "wasm32", no_main)]

mod state;

use std::sync::Arc;

use abi::swap::router::SwapAbi;
use async_graphql::{EmptySubscription, Object, Request, Response, Schema};
use linera_sdk::{
    base::{MessageId, WithServiceAbi},
    views::View,
    Service, ServiceRuntime,
};

use self::state::SwapState;

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

struct MutationRoot {
    runtime: Arc<ServiceRuntime<SwapService>>,
}

#[Object]
impl MutationRoot {
    async fn increment(&self, value: u64) -> [u8; 0] {
        self.runtime.schedule_operation(&value);
        []
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

    async fn rfq_chains(&self) -> Vec<MessageId> {
        self.state
            .rfq_chains
            .index_values()
            .await
            .unwrap()
            .into_iter()
            .map(|(_, message_id)| message_id)
            .collect()
    }
}

#[cfg(test)]
mod tests {
    use std::sync::Arc;

    use async_graphql::{Request, Response, Value};
    use futures::FutureExt as _;
    use linera_sdk::{util::BlockingWait, views::View, Service, ServiceRuntime};
    use serde_json::json;

    use super::{SwapService, SwapState};

    #[test]
    fn query() {}
}
