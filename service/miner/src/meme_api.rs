use std::sync::Arc;

use abi::{meme::MiningInfo, proxy::Chain};
use async_graphql::{Request, Variables};
use linera_base::{crypto::CryptoHash, data_types::Amount, identifiers::Account};
use linera_client::chain_listener::ClientContext;
use serde::Deserialize;

use crate::{errors::MemeMinerError, wallet_api::WalletApi};

#[derive(Debug, Deserialize)]
struct MineResponse {
    #[allow(dead_code)]
    mine: Vec<u8>,
}

#[derive(Debug, Deserialize)]
struct BalanceOfResponse {
    #[serde(alias = "balanceOf")]
    balance_of: Amount,
}

#[derive(Debug, Deserialize)]
struct MiningInfoResponse {
    #[serde(alias = "miningInfo")]
    mining_info: Option<MiningInfo>,
}

pub struct MemeApi<C>
where
    C: ClientContext,
{
    wallet: Arc<WalletApi<C>>,

    chain: Chain,
}

impl<C> MemeApi<C>
where
    C: ClientContext + 'static,
{
    pub fn new(chain: Chain, wallet: Arc<WalletApi<C>>) -> Self {
        Self { chain, wallet }
    }

    pub async fn mine(&self, nonce: CryptoHash) -> Result<(), MemeMinerError> {
        let mut request = Request::new(
            r#"
            mutation mine($nonce: CryptoHash!) {
                mine(nonce: $nonce)
            }
            "#,
        );

        request = request.variables(Variables::from_json(serde_json::json!({
            "nonce": nonce,
        })));
        let hash = self
            .wallet
            .execute_operation::<MineResponse>(
                self.chain.token.unwrap(),
                self.chain.chain_id,
                request,
            )
            .await?;
        tracing::debug!("Hash {:?}", hash);
        Ok(())
    }

    pub fn account(&self) -> Account {
        Account {
            chain_id: self.chain.chain_id,
            owner: self.wallet.owner(),
        }
    }

    pub async fn balance(&self, owner: Option<Account>) -> Result<Amount, MemeMinerError> {
        // Mining reward is on meme chain, user need to redeem to their own chain
        let account = owner.unwrap_or(self.account());
        let mut request = Request::new(
            r#"
            query balanceOf($owner: String!) {
                balanceOf(owner: $owner)
            }
            "#,
        );

        request = request.variables(Variables::from_json(serde_json::json!({
            "owner": account.to_string(),
        })));

        let outcome = self
            .wallet
            .query_user_application::<BalanceOfResponse>(
                self.chain.token.unwrap(),
                self.chain.chain_id,
                request,
            )
            .await?;
        Ok(outcome.response.data.balance_of)
    }

    pub async fn mining_info(&self) -> Result<Option<MiningInfo>, MemeMinerError> {
        let request = Request::new(
            r#"
            query miningInfo {
                miningInfo {
                    initialTarget
                    target
                    newTarget
                    blockDuration
                    targetBlockDuration
                    targetAdjustmentBlocks
                    emptyBlockRewardPercent
                    initialRewardAmount
                    halvingCycle
                    nextHalvingAt
                    rewardAmount
                    miningHeight
                    miningExecutions
                    previousNonce
                    miningStarted
                }
            }
            "#,
        );

        let outcome = self
            .wallet
            .query_user_application::<MiningInfoResponse>(
                self.chain.token.unwrap(),
                self.chain.chain_id,
                request,
            )
            .await?;
        Ok(outcome.response.data.mining_info)
    }
}
