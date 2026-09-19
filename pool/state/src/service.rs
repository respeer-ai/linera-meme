#![cfg_attr(target_arch = "wasm32", no_main)]

use abi::{
    meme_token::MemeToken,
    pool::{LiquidityAmount, Pool, state_v1::PoolStateAbi},
};
use async_graphql::{EmptyMutation, EmptySubscription, Object, Request, Response, Schema};
use linera_sdk::{
    linera_base_types::{Account, Amount, ApplicationId, WithServiceAbi},
    views::View,
    Service, ServiceRuntime,
};
use pool_state::state::PoolState;
use std::sync::Arc;

pub struct PoolStateService {
    state: Arc<PoolState>,
}

linera_sdk::service!(PoolStateService);

impl WithServiceAbi for PoolStateService {
    type Abi = PoolStateAbi;
}

impl Service for PoolStateService {
    type Parameters = ();

    async fn new(runtime: ServiceRuntime<Self>) -> Self {
        let state = PoolState::load(runtime.root_view_storage_context())
            .await
            .expect("Failed to load pool state v1");
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
    state: Arc<PoolState>,
}

#[Object]
impl QueryRoot {
    async fn health(&self) -> bool {
        true
    }

    async fn business_application_id(&self) -> Option<ApplicationId> {
        *self.state.business_application_id.get()
    }

    async fn operator(&self) -> Option<Account> {
        *self.state.operator.get()
    }

    async fn pool(&self) -> Option<Pool> {
        self.state.pool.get().clone()
    }

    async fn claimable_balance(
        &self,
        token: Option<ApplicationId>,
        owner: Account,
    ) -> Amount {
        self.state
            .claimable_balances
            .get(&MemeToken::from(token))
            .await
            .expect("Failed to read claimable balance")
            .and_then(|balances| balances.get(&owner).copied())
            .unwrap_or(Amount::ZERO)
    }

    async fn claiming_balance(
        &self,
        token: Option<ApplicationId>,
        owner: Account,
    ) -> Amount {
        self.state
            .claiming_balances
            .get(&MemeToken::from(token))
            .await
            .expect("Failed to read claiming balance")
            .and_then(|balances| balances.get(&owner).copied())
            .unwrap_or(Amount::ZERO)
    }

    async fn liquidity(&self, owner: Account) -> LiquidityAmount {
        let pool = self.state.pool.get().clone();
        let total_supply = *self.state.total_supply.get();
        let liquidity = self
            .state
            .shares
            .get(&owner)
            .await
            .expect("Failed to read liquidity")
            .unwrap_or(Amount::ZERO);
        let (amount_0, amount_1) = match &pool {
            Some(pool) if liquidity > Amount::ZERO => pool
                .try_calculate_liquidity_amount_pair(
                    liquidity,
                    total_supply.try_add(pool.mint_fee(total_supply)).unwrap(),
                    None,
                    None,
                )
                .unwrap_or((Amount::ZERO, Amount::ZERO)),
            _ => (Amount::ZERO, Amount::ZERO),
        };
        LiquidityAmount {
            liquidity,
            amount_0,
            amount_1,
        }
    }

    async fn total_supply(&self) -> Amount {
        let pool = self.state.pool.get().clone();
        let total_supply = *self.state.total_supply.get();
        match &pool {
            Some(pool) => total_supply.try_add(pool.mint_fee(total_supply)).unwrap(),
            None => total_supply,
        }
    }
}
