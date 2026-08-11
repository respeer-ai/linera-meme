#![cfg_attr(target_arch = "wasm32", no_main)]

use abi::meme::{Meme, MemeAbi, MemeOperation, MiningInfo};
use async_graphql::{EmptySubscription, Object, Request, Response, Schema};
use linera_sdk::{
    linera_base_types::{Account, Amount, ChainId, CryptoHash, WithServiceAbi},
    views::View,
    Service, ServiceRuntime,
};
use meme_app::state::{adapter::ServiceStateAdapter, MemeState};
use std::sync::Arc;

pub struct MemeService {
    runtime: Arc<ServiceRuntime<Self>>,
    state: Arc<MemeState>,
}

linera_sdk::service!(MemeService);

impl WithServiceAbi for MemeService {
    type Abi = MemeAbi;
}

impl Service for MemeService {
    type Parameters = ();

    async fn new(runtime: ServiceRuntime<Self>) -> Self {
        let state = MemeState::load(runtime.root_view_storage_context())
            .await
            .expect("Failed to load meme business state");
        Self {
            runtime: Arc::new(runtime),
            state: Arc::new(state),
        }
    }

    async fn handle_query(&self, request: Request) -> Response {
        Schema::build(
            QueryRoot {
                runtime: self.runtime.clone(),
                state: self.state.clone(),
            },
            MutationRoot {
                runtime: self.runtime.clone(),
            },
            EmptySubscription,
        )
        .finish()
        .execute(request)
        .await
    }
}

struct QueryRoot {
    runtime: Arc<ServiceRuntime<MemeService>>,
    state: Arc<MemeState>,
}

#[Object]
impl QueryRoot {
    async fn health(&self) -> bool {
        true
    }

    async fn total_supply(&self) -> Option<Amount> {
        self.state_adapter()
            .expect("Failed to create meme service state adapter")
            .total_supply()
            .await
            .expect("Failed to read total supply from state")
    }

    async fn balance_of(&self, owner: Account) -> Amount {
        self.state_adapter()
            .expect("Failed to create meme service state adapter")
            .balance_of(owner)
            .await
            .expect("Failed to read balance from state")
    }

    async fn allowance_of(&self, owner: Account, spender: Account) -> Amount {
        self.state_adapter()
            .expect("Failed to create meme service state adapter")
            .allowance_of(owner, spender)
            .await
            .expect("Failed to read allowance from state")
    }

    async fn initial_owner_balance(&self) -> Amount {
        self.state_adapter()
            .expect("Failed to create meme service state adapter")
            .initial_owner_balance()
            .await
            .expect("Failed to read initial owner balance from state")
    }

    async fn creator_chain_id(&self) -> ChainId {
        self.runtime.application_creator_chain_id()
    }

    async fn initial_owner(&self) -> String {
        self.state_adapter()
            .expect("Failed to create meme service state adapter")
            .owner()
            .await
            .expect("Failed to read initial owner from state")
            .to_string()
    }

    async fn meme(&self) -> Option<Meme> {
        self.state_adapter()
            .expect("Failed to create meme service state adapter")
            .meme()
            .await
            .expect("Failed to read meme from state")
    }

    async fn mining_info(&self) -> Option<MiningInfo> {
        self.state_adapter()
            .expect("Failed to create meme service state adapter")
            .mining_info()
            .await
            .expect("Failed to read mining info from state")
    }
}

struct MutationRoot {
    runtime: Arc<ServiceRuntime<MemeService>>,
}

#[Object]
impl MutationRoot {
    async fn mint(&self, to: Account, amount: Amount) -> [u8; 0] {
        self.runtime
            .schedule_operation(&MemeOperation::Mint { to, amount });
        []
    }

    async fn mine(&self, nonce: CryptoHash) -> [u8; 0] {
        self.runtime
            .schedule_operation(&MemeOperation::Mine { nonce });
        []
    }

    async fn redeem(&self, amount: Option<Amount>) -> [u8; 0] {
        self.runtime
            .schedule_operation(&MemeOperation::Redeem { amount });
        []
    }
}

impl QueryRoot {
    fn state_adapter(
        &self,
    ) -> Result<ServiceStateAdapter<MemeService>, meme_app::state::errors::StateError> {
        ServiceStateAdapter::new(self.runtime.clone(), self.state.clone())
    }
}

#[cfg(test)]
mod service_tests;
