use std::sync::Arc;

use crate::state::PoolState;
use abi::application_state_base::{decode_response_field, LocalStateInterface};
use abi::pool::{LiquidityAmount, Pool, state_v1::PoolStateAbi as PoolStateV1Abi};
use async_graphql::{Request, Variables};
use linera_sdk::{
    Service, ServiceRuntime,
    linera_base_types::{Account, Amount, ApplicationId},
};
use serde::de::DeserializeOwned;
use serde_json::json;

use super::StateError;

pub struct ServiceStateAdapter<S: Service> {
    runtime: Arc<ServiceRuntime<S>>,
    state: Arc<PoolState>,
}

impl<S: Service> ServiceStateAdapter<S> {
    pub fn new(
        runtime: Arc<ServiceRuntime<S>>,
        state: Arc<PoolState>,
    ) -> Result<Self, StateError> {
        Ok(Self { runtime, state })
    }

    async fn query_state<T: DeserializeOwned>(
        &self,
        request: Request,
        field: &'static str,
    ) -> Result<T, StateError> {
        let state_application_id = self.state.latest_state_application().await?;
        Ok(decode_response_field(
            self.runtime.query_application(
                state_application_id.with_abi::<PoolStateV1Abi>(),
                &request,
            ),
            field,
        )?)
    }

    pub async fn pool(&self) -> Result<Option<Pool>, StateError> {
        self.query_state(Request::new("query { pool }"), "pool")
            .await
    }

    pub async fn claimable_balance(
        &self,
        token: Option<ApplicationId>,
        owner: Account,
    ) -> Result<Amount, StateError> {
        let request = Request::new(
            "query ClaimableBalance($token: ApplicationId, $owner: Account!) { claimableBalance(token: $token, owner: $owner) }",
        )
        .variables(Variables::from_json(json!({
            "token": token.map(|id| id.to_string()),
            "owner": {
                "chain_id": owner.chain_id.to_string(),
                "owner": owner.owner.to_string(),
            }
        })));
        self.query_state(request, "claimableBalance").await
    }

    pub async fn liquidity(&self, owner: Account) -> Result<LiquidityAmount, StateError> {
        let request = Request::new(
            "query Liquidity($owner: Account!) { liquidity(owner: $owner) { liquidity amount0 amount1 } }",
        )
        .variables(Variables::from_json(json!({
            "owner": {
                "chain_id": owner.chain_id.to_string(),
                "owner": owner.owner.to_string(),
            }
        })));
        self.query_state(request, "liquidity").await
    }

    pub async fn total_supply(&self) -> Result<Amount, StateError> {
        self.query_state(Request::new("query { totalSupply }"), "totalSupply")
            .await
    }
}
