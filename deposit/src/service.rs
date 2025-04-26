#![cfg_attr(target_arch = "wasm32", no_main)]

mod state;

use self::state::DepositState;
use abi::deposit::{DepositAbi, DepositOperation};
use async_graphql::{EmptySubscription, Object, Schema};
use linera_sdk::{
    graphql::GraphQLMutationRoot, linera_base_types::WithServiceAbi, views::View, Service,
    ServiceRuntime,
};
use std::sync::Arc;

use deposit::Deposit;

pub struct ApplicationService {
    state: Arc<DepositState>,
    runtime: Arc<ServiceRuntime<Self>>,
}

linera_sdk::service!(ApplicationService);

impl WithServiceAbi for ApplicationService {
    type Abi = DepositAbi;
}

impl Service for ApplicationService {
    type Parameters = ();

    async fn new(runtime: ServiceRuntime<Self>) -> Self {
        let state = DepositState::load(runtime.root_view_storage_context())
            .await
            .expect("Failed to load state");
        ApplicationService {
            state: Arc::new(state),
            runtime: Arc::new(runtime),
        }
    }

    async fn handle_query(&self, query: Self::Query) -> Self::QueryResponse {
        let schema = Schema::build(
            QueryRoot {
                state: self.state.clone(),
            },
            DepositOperation::mutation_root(self.runtime.clone()),
            EmptySubscription,
        )
        .finish();
        schema.execute(query).await
    }
}

struct QueryRoot {
    state: Arc<DepositState>,
}

#[Object]
impl QueryRoot {
    async fn deposits(&self) -> Vec<Deposit> {
        self.state
            .deposits
            .elements()
            .await
            .expect("Failed get deposits")
    }
}
