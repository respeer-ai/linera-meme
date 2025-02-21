// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

use abi::approval::Approval;
use linera_sdk::{
    base::{BytecodeId, ChainId, MessageId, Owner, Timestamp},
    views::{linera_views, MapView, RegisterView, RootView, ViewStorageContext},
};
use proxy::{Chain, GenesisMiner, InstantiationArgument, Miner, ProxyError};
use std::collections::HashMap;

/// The application state.
#[derive(RootView)]
#[view(context = "ViewStorageContext")]
pub struct ProxyState {
    pub meme_bytecode_id: RegisterView<Option<BytecodeId>>,
    /// Operator and banned
    pub operators: MapView<Owner, bool>,
    /// Genesis miner and approvals it should get
    pub genesis_miners: MapView<Owner, GenesisMiner>,
    /// Removing candidates of genesis miner
    pub removing_genesis_miners: MapView<Owner, Approval>,
    /// Miners and mining chains (ignore permissionless chain)
    pub miners: MapView<Owner, Miner>,
    /// Chains aleady created
    pub chains: MapView<ChainId, Chain>,
}

#[allow(dead_code)]
impl ProxyState {
    pub(crate) async fn initantiate(
        &mut self,
        argument: InstantiationArgument,
        owner: Owner,
    ) -> Result<(), ProxyError> {
        self.meme_bytecode_id.set(Some(argument.meme_bytecode_id));
        self.operators.insert(&argument.operator, false)?;
        Ok(self.operators.insert(&owner, false)?)
    }

    async fn initial_approval(&self) -> Result<Approval, ProxyError> {
        let operators = self.operators.count().await?;
        Ok(Approval {
            approvers: HashMap::new(),
            least_approvals: std::cmp::max(operators * 2 / 3, 1),
        })
    }

    pub(crate) async fn add_genesis_miner(
        &mut self,
        owner: Owner,
        endpoint: Option<String>,
    ) -> Result<(), ProxyError> {
        if !self.genesis_miners.contains_key(&owner).await? {
            let approval = self.initial_approval().await?;
            return Ok(self.genesis_miners.insert(
                &owner,
                GenesisMiner {
                    owner,
                    endpoint,
                    approval,
                },
            )?);
        }
        Ok(())
    }

    pub(crate) async fn approve_add_genesis_miner(
        &mut self,
        owner: Owner,
        signer: Owner,
    ) -> Result<(), ProxyError> {
        let mut miner = self.genesis_miners.get(&owner).await?.unwrap();
        if miner.approval.approvers.contains_key(&signer) {
            return Ok(());
        }
        miner.approval.approvers.insert(signer, true);
        Ok(self.genesis_miners.insert(&owner, miner)?)
    }

    pub(crate) async fn genesis_miners(&self) -> Result<Vec<Owner>, ProxyError> {
        let mut miners = Vec::new();
        self.genesis_miners
            .for_each_index_value(|owner, miner| {
                let approval = miner.into_owned().approval;
                if approval.approvers.len() >= approval.least_approvals {
                    miners.push(owner);
                }
                Ok(())
            })
            .await?;
        Ok(miners)
    }

    pub(crate) async fn miners(&self) -> Result<Vec<Owner>, ProxyError> {
        Ok(self.miners.indices().await?)
    }

    pub(crate) async fn validate_operator(&self, owner: Owner) -> Result<bool, ProxyError> {
        Ok(self.operators.contains_key(&owner).await?)
    }

    pub(crate) async fn remove_genesis_miner(&mut self, owner: Owner) -> Result<(), ProxyError> {
        if self.removing_genesis_miners.contains_key(&owner).await? {
            return Ok(());
        }
        if !self.genesis_miners.contains_key(&owner).await? {
            return Err(ProxyError::NotExists);
        }
        let approval = self.initial_approval().await?;
        Ok(self.removing_genesis_miners.insert(&owner, approval)?)
    }

    pub(crate) async fn approve_remove_genesis_miner(
        &mut self,
        owner: Owner,
        signer: Owner,
    ) -> Result<(), ProxyError> {
        let mut miner = self.removing_genesis_miners.get(&owner).await?.unwrap();
        if miner.approvers.contains_key(&signer) {
            return Ok(());
        }
        miner.approvers.insert(signer, true);
        if miner.approvers.len() >= miner.least_approvals {
            self.removing_genesis_miners.remove(&owner)?;
            return Ok(self.genesis_miners.remove(&owner)?);
        }
        Ok(self.removing_genesis_miners.insert(&owner, miner)?)
    }

    pub(crate) async fn meme_bytecode_id(&self) -> BytecodeId {
        self.meme_bytecode_id.get().unwrap()
    }

    pub(crate) async fn create_chain(
        &mut self,
        chain_id: ChainId,
        message_id: MessageId,
        timestamp: Timestamp,
    ) -> Result<(), ProxyError> {
        Ok(self.chains.insert(
            &chain_id,
            Chain {
                chain_id,
                message_id,
                created_at: timestamp,
            },
        )?)
    }
}
