use std::sync::Arc;

use abi::proxy::{Chain, Miner};
use async_graphql::{Request, Variables};
use linera_base::identifiers::{ApplicationId, ChainId};
use linera_client::chain_listener::ClientContext;
use serde::Deserialize;

use crate::{errors::MemeMinerError, wallet_api::WalletApi};

#[derive(Debug, Deserialize)]
struct MinerResponse {
    #[serde(alias = "miner")]
    miner: Option<Miner>,
}

#[derive(Debug, Deserialize)]
struct MinerRegisteredResponse {
    #[serde(alias = "minerRegistered")]
    miner_registered: bool,
}

#[derive(Debug, Deserialize)]
struct RegisterMinerResponse {
    #[allow(dead_code)]
    #[serde(alias = "registerMiner")]
    register_miner: Vec<u8>,
}

#[derive(Debug, Deserialize)]
struct MemeChainsResponse {
    #[serde(alias = "memeChains")]
    meme_chains: Vec<Chain>,
}

pub struct ProxyApi<C>
where
    C: ClientContext,
{
    wallet: Arc<WalletApi<C>>,

    application_id: ApplicationId,
}

impl<C> ProxyApi<C>
where
    C: ClientContext + 'static,
{
    pub fn new(application_id: ApplicationId, wallet: Arc<WalletApi<C>>) -> Self {
        Self {
            application_id,
            wallet,
        }
    }

    pub async fn creator_chain_id(&self) -> Result<ChainId, MemeMinerError> {
        self.wallet
            .application_creator_chain_id(self.application_id)
            .await
    }

    pub async fn follow_chain(&self) -> Result<(), MemeMinerError> {
        let creator_chain_id = self.creator_chain_id().await?;
        self.wallet.follow_chain(creator_chain_id).await
    }

    pub async fn miner_registered(&self) -> Result<bool, MemeMinerError> {
        let creator_chain_id = self.creator_chain_id().await?;

        let mut request = Request::new(
            r#"
            query minerRegistered($owner: String!) {
                minerRegistered(owner: $owner)
            }
            "#,
        );
        request = request.variables(Variables::from_json(serde_json::json!({
            "owner": self.wallet.owner(),
        })));

        let outcome = self
            .wallet
            .query_user_application::<MinerRegisteredResponse>(
                self.application_id,
                creator_chain_id,
                request,
            )
            .await?;
        Ok(outcome.response.data.miner_registered)
    }

    #[allow(dead_code)]
    pub async fn miner(&self) -> Result<Option<Miner>, MemeMinerError> {
        let creator_chain_id = self.creator_chain_id().await?;

        let mut request = Request::new(
            r#"
            query miner($owner: String!) {
                miner(owner: $owner) {
                    owner
                    registeredAt
                }
            }
            "#,
        );
        request = request.variables(Variables::from_json(serde_json::json!({
            "owner": self.wallet.owner(),
        })));

        let outcome = self
            .wallet
            .query_user_application::<MinerResponse>(self.application_id, creator_chain_id, request)
            .await?;
        Ok(outcome.response.data.miner)
    }

    pub async fn register_miner(&self) -> Result<(), MemeMinerError> {
        let request = Request::new(
            r#"
            mutation registerMiner {
                registerMiner
            }
            "#,
        );
        let hash = self
            .wallet
            .execute_operation::<RegisterMinerResponse>(
                self.application_id,
                self.wallet.default_chain(),
                request,
            )
            .await?;
        tracing::debug!("Hash {:?}", hash);
        Ok(())
    }

    pub fn application_id(&self) -> ApplicationId {
        self.application_id
    }

    pub async fn meme_chains(&self) -> Result<Vec<Chain>, MemeMinerError> {
        let creator_chain_id = self.creator_chain_id().await?;

        let mut request = Request::new(
            r#"
            query memeChains($createdAfter: Timestamp) {
                memeChains(createdAfter: $createdAfter) {
                    chainId
                    createdAt
                    token
                }
            }
            "#,
        );

        request = request.variables(Variables::from_json(serde_json::json!({
            // Every miner can mine every meme chain right now
            "createdAfter": 0,
        })));

        let outcome = self
            .wallet
            .query_user_application::<MemeChainsResponse>(
                self.application_id,
                creator_chain_id,
                request,
            )
            .await?;
        Ok(outcome.response.data.meme_chains)
    }
}
