#![cfg_attr(target_arch = "wasm32", no_main)]

use abi::state::StateAbi;
use async_graphql::{EmptyMutation, EmptySubscription, Object, Request, Response, Schema};
use linera_sdk::{
    linera_base_types::{ApplicationId, WithServiceAbi},
    views::View,
    Service, ServiceRuntime,
};
use state::{state::State, state_key::StateKey};
use std::sync::Arc;

pub struct StateService {
    state: Arc<State>,
}

linera_sdk::service!(StateService);

impl WithServiceAbi for StateService {
    type Abi = StateAbi;
}

impl Service for StateService {
    type Parameters = ();

    async fn new(runtime: ServiceRuntime<Self>) -> Self {
        let state = State::load(runtime.root_view_storage_context())
            .await
            .expect("Failed to load state");
        StateService {
            state: Arc::new(state),
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
    state: Arc<State>,
}

#[Object]
impl QueryRoot {
    async fn ready(&self) -> bool {
        true
    }

    async fn read(
        &self,
        namespace: u8,
        application_id: ApplicationId,
        key: Vec<u8>,
    ) -> Option<Vec<u8>> {
        let slot = self.application_slot(namespace, application_id).await?;
        self.state
            .records
            .get(&StateKey::new(namespace, slot, key).into_bytes())
            .await
            .expect("Failed to read state record")
    }

    async fn batch_read(
        &self,
        namespace: u8,
        application_id: ApplicationId,
        keys: Vec<Vec<u8>>,
    ) -> Vec<Option<Vec<u8>>> {
        let Some(slot) = self.application_slot(namespace, application_id).await else {
            return vec![None; keys.len()];
        };
        let mut values = Vec::with_capacity(keys.len());
        for key in keys {
            values.push(
                self.state
                    .records
                    .get(&StateKey::new(namespace, slot, key).into_bytes())
                    .await
                    .expect("Failed to batch read state record"),
            );
        }
        values
    }
}

impl QueryRoot {
    async fn application_slot(&self, namespace: u8, application_id: ApplicationId) -> Option<u8> {
        let applications = self
            .state
            .namespace_apps
            .get(&namespace)
            .await
            .expect("Failed to read namespace applications")?;
        applications
            .iter()
            .position(|application| *application == application_id)
            .and_then(|slot| slot.try_into().ok())
    }
}
