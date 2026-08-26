use std::sync::Arc;

use crate::state::ProxyState;
use abi::{
    application_state_base::{decode_response_field, LocalStateInterface},
    proxy::{state_v1::ProxyStateAbi as ProxyStateV1Abi, Chain, Miner},
};
use async_graphql::{Request, Variables};
use linera_sdk::{
    linera_base_types::{Account, AccountOwner, ApplicationId, ChainId, ModuleId, Timestamp},
    Service, ServiceRuntime,
};
use serde::de::DeserializeOwned;
use serde_json::json;

use super::StateError;

pub struct ServiceStateAdapter<S: Service> {
    runtime: Arc<ServiceRuntime<S>>,
    state: Arc<ProxyState>,
}

impl<S: Service> ServiceStateAdapter<S> {
    pub fn new(
        runtime: Arc<ServiceRuntime<S>>,
        state: Arc<ProxyState>,
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
                state_application_id.with_abi::<ProxyStateV1Abi>(),
                &request,
            ),
            field,
        )?)
    }

    pub async fn meme_bytecode_id(&self) -> Result<ModuleId, StateError> {
        self.query_state(Request::new("query { memeBytecodeId }"), "memeBytecodeId")
            .await
    }

    pub async fn swap_application_id(&self) -> Result<ApplicationId, StateError> {
        self.query_state(
            Request::new("query { swapApplicationId }"),
            "swapApplicationId",
        )
        .await
    }

    pub async fn genesis_miners(&self) -> Result<Vec<Miner>, StateError> {
        self.query_state(
            Request::new("query { genesisMiners { owner registeredAt } }"),
            "genesisMiners",
        )
        .await
    }

    pub async fn miners(&self) -> Result<Vec<Miner>, StateError> {
        self.query_state(
            Request::new("query { miners { owner registeredAt } }"),
            "miners",
        )
        .await
    }

    pub async fn miner_owners(&self) -> Result<Vec<AccountOwner>, StateError> {
        self.query_state(Request::new("query { minerOwners }"), "minerOwners")
            .await
    }

    pub async fn is_genesis_miner(&self, owner: Account) -> Result<bool, StateError> {
        self.query_state(
            Request::new(
                "query IsGenesisMiner($owner: Account!) { isGenesisMiner(owner: $owner) }",
            )
            .variables(Variables::from_json(json!({
                "owner": {
                    "chain_id": owner.chain_id.to_string(),
                    "owner": owner.owner.to_string(),
                }
            }))),
            "isGenesisMiner",
        )
        .await
    }

    pub async fn chain(&self, chain_id: ChainId) -> Result<Option<Chain>, StateError> {
        self.query_state(
            Request::new(
                "query Chain($chainId: ChainId!) { chain(chainId: $chainId) { chainId createdAt token } }",
            )
            .variables(Variables::from_json(json!({
                "chainId": chain_id.to_string(),
            }))),
            "chain",
        )
        .await
    }

    pub async fn chains(
        &self,
        created_after: Option<Timestamp>,
    ) -> Result<Vec<Chain>, StateError> {
        self.query_state(
            Request::new(
                "query Chains($createdAfter: Timestamp) { chains(createdAfter: $createdAfter) { chainId createdAt token } }",
            )
            .variables(Variables::from_json(json!({
                "createdAfter": created_after,
            }))),
            "chains",
        )
        .await
    }

    pub async fn chain_by_token(
        &self,
        token: ApplicationId,
    ) -> Result<Option<Chain>, StateError> {
        self.query_state(
            Request::new(
                "query ChainByToken($token: ApplicationId!) { chainByToken(token: $token) { chainId createdAt token } }",
            )
            .variables(Variables::from_json(json!({
                "token": token.to_string(),
            }))),
            "chainByToken",
        )
        .await
    }
}
