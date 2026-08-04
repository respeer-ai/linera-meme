#![cfg_attr(target_arch = "wasm32", no_main)]

use abi::meme::{Meme, MemeStateAbi, MiningInfo};
use async_graphql::{EmptyMutation, EmptySubscription, Object, Request, Response, Schema};
use linera_sdk::{
    linera_base_types::{Account, Amount, ApplicationId, WithServiceAbi},
    views::View,
    Service, ServiceRuntime,
};
use meme_state::state::MemeState;
use std::sync::Arc;

pub struct MemeStateService {
    state: Arc<MemeState>,
}

linera_sdk::service!(MemeStateService);

impl WithServiceAbi for MemeStateService {
    type Abi = MemeStateAbi;
}

impl Service for MemeStateService {
    type Parameters = ();

    async fn new(runtime: ServiceRuntime<Self>) -> Self {
        let state = MemeState::load(runtime.root_view_storage_context())
            .await
            .expect("Failed to load meme state v1");
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
    state: Arc<MemeState>,
}

#[Object]
impl QueryRoot {
    async fn health(&self) -> bool {
        true
    }

    async fn balance(&self, owner: Account) -> Amount {
        self.state
            .balances
            .get(&owner)
            .await
            .expect("Failed to read balance from state")
            .unwrap_or(Amount::ZERO)
    }

    async fn allowance(&self, owner: Account, spender: Account) -> Amount {
        self.state
            .allowances
            .get(&owner)
            .await
            .expect("Failed to read allowance from state")
            .map(|allowances| allowances.get(&spender).copied().unwrap_or(Amount::ZERO))
            .unwrap_or(Amount::ZERO)
    }

    async fn owner(&self) -> Option<Account> {
        self.state.owner.get().clone()
    }

    async fn mining_info(&self) -> Option<MiningInfo> {
        self.state.mining_info.get().clone()
    }

    async fn proxy_application_id(&self) -> Option<ApplicationId> {
        self.state.proxy_application_id.get().clone()
    }

    async fn swap_application_id(&self) -> Option<ApplicationId> {
        self.state.swap_application_id.get().clone()
    }

    async fn initial_owner_balance(&self) -> Amount {
        *self.state.initial_owner_balance.get()
    }

    async fn meme(&self) -> Option<Meme> {
        self.state.meme.get().clone()
    }

    async fn total_supply(&self) -> Option<Amount> {
        self.state.meme.get().as_ref().map(|meme| meme.total_supply)
    }
}
