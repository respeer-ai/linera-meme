use std::{cmp::Ordering, collections::HashMap, str::FromStr, sync::Arc, time::Instant};

use abi::{
    hash::{hash_cmp, hash_increment},
    meme::{MemeAbi, MiningBase, MiningInfo},
    proxy::{Chain, Miner, ProxyAbi},
};
use async_graphql::{Request, Value, Variables};
use futures::{lock::Mutex, FutureExt as _};
use linera_base::{
    crypto::CryptoHash,
    data_types::{Amount, BlockHeight},
    identifiers::{Account, AccountOwner, ApplicationId, ChainId},
};
use linera_client::chain_listener::{ChainListener, ChainListenerConfig, ClientContext};
use linera_core::data_types::ClientOutcome;
use linera_execution::{Query, QueryOutcome, QueryResponse};
use linera_service::util;
use serde::{de::DeserializeOwned, Deserialize};
use tokio::{
    sync::Notify,
    task::JoinHandle,
    time::{sleep, Duration},
};
use tokio_util::sync::CancellationToken;

use crate::{errors::MemeMinerError, wallet_api::WalletApi};

#[derive(Debug, Deserialize)]
struct MineResponse {
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

    pub async fn creator_chain_id(&self) -> Result<ChainId, MemeMinerError> {
        self.wallet
            .application_creator_chain_id(self.chain.token.unwrap())
            .await
    }

    pub async fn follow_chain(&self) -> Result<(), MemeMinerError> {
        let creator_chain_id = self.creator_chain_id().await?;
        self.wallet.follow_chain(creator_chain_id).await
    }

    pub fn application_id(&self) -> ApplicationId {
        self.chain.token.unwrap()
    }

    pub async fn mine(&self, nonce: CryptoHash) -> Result<(), MemeMinerError> {
        // TODO: also process maker deal here
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
        tracing::info!("Hash {:?}", hash);
        Ok(())
    }

    pub async fn balance(&self) -> Result<Amount, MemeMinerError> {
        // Mining reward is on meme chain, user need to redeem to their own chain
        let account = Account {
            chain_id: self.chain.chain_id,
            owner: self.wallet.owner(),
        };
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
