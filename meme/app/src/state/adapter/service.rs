use crate::state::MemeState;
use abi::{
    application_state_base::{decode_response_field, LocalStateInterface},
    meme::{state_v1::MemeStateAbi as MemeStateV1Abi, Meme, MiningInfo},
};
use async_graphql::{Request, Variables};
use linera_sdk::{
    linera_base_types::{Account, Amount, ApplicationId},
    Service, ServiceRuntime,
};
use serde_json::json;
use std::sync::Arc;

use super::StateError;

pub struct ServiceStateAdapter<S: Service> {
    runtime: Arc<ServiceRuntime<S>>,
    state: Arc<MemeState>,
}

impl<S: Service> ServiceStateAdapter<S> {
    pub fn new(
        runtime: Arc<ServiceRuntime<S>>,
        state: Arc<MemeState>,
    ) -> Result<Self, StateError> {
        Ok(Self { runtime, state })
    }

    async fn state_application_id(&self) -> Result<ApplicationId, StateError> {
        self.state.latest_state_application().await
    }

    pub async fn owner(&self) -> Result<Account, StateError> {
        let state_application_id = self.state_application_id().await?;
        let request = Request::new("query { owner }");
        let response = self
            .runtime
            .query_application(state_application_id.with_abi::<MemeStateV1Abi>(), &request);
        Ok(decode_response_field(response, "owner")?)
    }

    pub async fn balance_of(&self, owner: Account) -> Result<Amount, StateError> {
        let state_application_id = self.state_application_id().await?;
        let request = Request::new("query Balance($owner: Account!) { balance(owner: $owner) }")
            .variables(Variables::from_json(json!({
                "owner": {
                    "chain_id": owner.chain_id.to_string(),
                    "owner": owner.owner.to_string(),
                }
            })));
        let response = self
            .runtime
            .query_application(state_application_id.with_abi::<MemeStateV1Abi>(), &request);
        Ok(decode_response_field(response, "balance")?)
    }

    pub async fn allowance_of(
        &self,
        owner: Account,
        spender: Account,
    ) -> Result<Amount, StateError> {
        let state_application_id = self.state_application_id().await?;
        let request = Request::new(
            "query Allowance($owner: Account!, $spender: Account!) { allowance(owner: $owner, spender: $spender) }",
        )
        .variables(Variables::from_json(json!({
            "owner": {
                "chain_id": owner.chain_id.to_string(),
                "owner": owner.owner.to_string(),
            },
            "spender": {
                "chain_id": spender.chain_id.to_string(),
                "owner": spender.owner.to_string(),
            }
        })));
        let response = self
            .runtime
            .query_application(state_application_id.with_abi::<MemeStateV1Abi>(), &request);
        Ok(decode_response_field(response, "allowance")?)
    }

    pub async fn mining_info(&self) -> Result<MiningInfo, StateError> {
        let state_application_id = self.state_application_id().await?;
        let request = Request::new("query { miningInfo }");
        let response = self
            .runtime
            .query_application(state_application_id.with_abi::<MemeStateV1Abi>(), &request);
        Ok(decode_response_field(response, "miningInfo")?)
    }

    pub async fn swap_application_id(&self) -> Result<Option<ApplicationId>, StateError> {
        let state_application_id = self.state_application_id().await?;
        let request = Request::new("query { swapApplicationId }");
        let response = self
            .runtime
            .query_application(state_application_id.with_abi::<MemeStateV1Abi>(), &request);
        Ok(decode_response_field(response, "swapApplicationId")?)
    }

    pub async fn proxy_application_id(&self) -> Result<Option<ApplicationId>, StateError> {
        let state_application_id = self.state_application_id().await?;
        let request = Request::new("query { proxyApplicationId }");
        let response = self
            .runtime
            .query_application(state_application_id.with_abi::<MemeStateV1Abi>(), &request);
        Ok(decode_response_field(response, "proxyApplicationId")?)
    }

    pub async fn initial_owner_balance(&self) -> Result<Amount, StateError> {
        let state_application_id = self.state_application_id().await?;
        let request = Request::new("query { initialOwnerBalance }");
        let response = self
            .runtime
            .query_application(state_application_id.with_abi::<MemeStateV1Abi>(), &request);
        Ok(decode_response_field(response, "initialOwnerBalance")?)
    }

    pub async fn meme(&self) -> Result<Option<Meme>, StateError> {
        let state_application_id = self.state_application_id().await?;
        let request = Request::new("query { meme }");
        let response = self
            .runtime
            .query_application(state_application_id.with_abi::<MemeStateV1Abi>(), &request);
        Ok(decode_response_field(response, "meme")?)
    }

    pub async fn total_supply(&self) -> Result<Option<Amount>, StateError> {
        let state_application_id = self.state_application_id().await?;
        let request = Request::new("query { totalSupply }");
        let response = self
            .runtime
            .query_application(state_application_id.with_abi::<MemeStateV1Abi>(), &request);
        Ok(decode_response_field(response, "totalSupply")?)
    }
}
