// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

use abi::{
    approval::Approval,
    proxy::{Chain, GenesisMiner, InstantiationArgument, Miner},
};
use linera_sdk::{
    linera_base_types::{
        Account, AccountOwner, ApplicationId, ChainId, MessageId, ModuleId, Timestamp,
    },
    views::{linera_views, MapView, RegisterView, RootView, ViewStorageContext},
};
use proxy::ProxyError;

/// The application state.
#[derive(RootView)]
#[view(context = "ViewStorageContext")]
pub struct ProxyState {
    pub meme_bytecode_id: RegisterView<Option<ModuleId>>,
    /// Active operators
    pub operators: MapView<Account, Approval>,
    /// Banning operators waiting for approval
    pub banning_operators: MapView<Account, Approval>,
    /// Genesis miner and approvals it should get
    pub genesis_miners: MapView<Account, GenesisMiner>,
    /// Removing candidates of genesis miner
    pub removing_genesis_miners: MapView<Account, Approval>,
    /// Miners and mining chains (ignore permissionless chain)
    pub miners: MapView<Account, Miner>,
    /// Chains aleady created
    pub chains: MapView<ChainId, Chain>,
    /// Swap application id for liquidity initialization
    pub swap_application_id: RegisterView<Option<ApplicationId>>,
}

#[allow(dead_code)]
impl ProxyState {
    pub(crate) async fn instantiate(
        &mut self,
        argument: InstantiationArgument,
        owners: Vec<Account>,
    ) -> Result<(), ProxyError> {
        self.meme_bytecode_id.set(Some(argument.meme_bytecode_id));

        for operator in argument.operators {
            let mut approval = Approval::new(1);
            approval.approve(owners[0]);
            self.operators.insert(&operator, approval)?;
        }

        self.swap_application_id
            .set(Some(argument.swap_application_id));

        for owner in owners {
            let mut approval = Approval::new(1);
            approval.approve(owner);
            self.genesis_miners.insert(
                &owner,
                GenesisMiner {
                    owner,
                    approval: approval.clone(),
                },
            )?;
            // We don't add owner as operator in default. Operator should be added with clear
            // definition
        }

        Ok(())
    }

    async fn initial_approval(&self) -> Result<Approval, ProxyError> {
        let operators = self.operators.count().await?;
        Ok(Approval::new(std::cmp::max(operators * 2 / 3, 1)))
    }

    pub(crate) async fn add_genesis_miner(&mut self, owner: Account) -> Result<(), ProxyError> {
        assert!(
            !self.genesis_miners.contains_key(&owner).await?,
            "Already exists",
        );
        let approval = self.initial_approval().await?;
        Ok(self
            .genesis_miners
            .insert(&owner, GenesisMiner { owner, approval })?)
    }

    pub(crate) async fn approve_add_genesis_miner(
        &mut self,
        owner: Account,
        operator: Account,
    ) -> Result<(), ProxyError> {
        let mut miner = self.genesis_miners.get(&owner).await?.unwrap();
        assert!(!miner.approval.voted(operator), "Already voted");
        miner.approval.approve(operator);
        Ok(self.genesis_miners.insert(&owner, miner)?)
    }

    pub(crate) async fn genesis_miners(&self) -> Result<Vec<Account>, ProxyError> {
        let mut miners = Vec::new();
        self.genesis_miners
            .for_each_index_value(|owner, miner| {
                let approval = miner.into_owned().approval;
                if approval.approved() {
                    miners.push(owner);
                }
                Ok(())
            })
            .await?;
        Ok(miners)
    }

    pub(crate) async fn genesis_miner_owners(&self) -> Result<Vec<AccountOwner>, ProxyError> {
        Ok(self
            .genesis_miners()
            .await?
            .into_iter()
            .map(|owner| owner.owner)
            .collect())
    }

    pub(crate) async fn miners(&self) -> Result<Vec<Account>, ProxyError> {
        Ok(self.miners.indices().await?)
    }

    pub(crate) async fn miner_owners(&self) -> Result<Vec<AccountOwner>, ProxyError> {
        Ok(self
            .miners()
            .await?
            .into_iter()
            .map(|owner| owner.owner)
            .collect())
    }

    pub(crate) async fn validate_operator(&self, owner: Account) -> Result<(), ProxyError> {
        let approval = self.operators.get(&owner).await?.unwrap();
        assert!(approval.approved(), "Invalid operator");
        Ok(())
    }

    pub(crate) async fn add_operator(&mut self, owner: Account) -> Result<(), ProxyError> {
        assert!(
            !self.operators.contains_key(&owner).await?,
            "Already exists",
        );
        let approval = self.initial_approval().await?;
        Ok(self.operators.insert(&owner, approval)?)
    }

    // Owner is approved operator, operator is voter
    pub(crate) async fn approve_add_operator(
        &mut self,
        owner: Account,
        operator: Account,
    ) -> Result<(), ProxyError> {
        let mut approval = self.operators.get(&owner).await?.unwrap();
        assert!(!approval.voted(operator), "Already voted");
        approval.approve(operator);
        Ok(self.operators.insert(&owner, approval)?)
    }

    pub(crate) async fn ban_operator(&mut self, owner: Account) -> Result<(), ProxyError> {
        assert!(
            self.operators.contains_key(&owner).await?,
            "Invalid operator"
        );
        assert!(
            !self.banning_operators.contains_key(&owner).await?,
            "Already exists",
        );
        let approval = self.initial_approval().await?;
        Ok(self.banning_operators.insert(&owner, approval)?)
    }

    // Owner is approved operator, operator is voter
    pub(crate) async fn approve_ban_operator(
        &mut self,
        owner: Account,
        operator: Account,
    ) -> Result<(), ProxyError> {
        assert!(
            self.banning_operators.contains_key(&owner).await?,
            "Invalid operator",
        );
        let mut approval = self.banning_operators.get(&owner).await?.unwrap();
        assert!(!approval.voted(operator), "Already voted");
        approval.approve(operator);
        if approval.approved() {
            self.banning_operators.remove(&owner)?;
            return Ok(self.operators.remove(&owner)?);
        }
        Ok(self.operators.insert(&owner, approval)?)
    }

    pub(crate) async fn remove_genesis_miner(&mut self, owner: Account) -> Result<(), ProxyError> {
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
        owner: Account,
        operator: Account,
    ) -> Result<(), ProxyError> {
        let mut approval = self.removing_genesis_miners.get(&owner).await?.unwrap();
        assert!(!approval.voted(operator), "Already voted");
        approval.approve(operator);
        if approval.approved() {
            self.removing_genesis_miners.remove(&owner)?;
            return Ok(self.genesis_miners.remove(&owner)?);
        }
        Ok(self.removing_genesis_miners.insert(&owner, approval)?)
    }

    pub(crate) async fn meme_bytecode_id(&self) -> ModuleId {
        self.meme_bytecode_id.get().unwrap()
    }

    pub(crate) async fn swap_application_id(&self) -> ApplicationId {
        self.swap_application_id.get().unwrap()
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
                token: None,
            },
        )?)
    }

    pub(crate) async fn create_chain_token(
        &mut self,
        chain_id: ChainId,
        token: ApplicationId,
    ) -> Result<(), ProxyError> {
        let mut chain = self.chains.get(&chain_id).await?.unwrap();
        assert!(chain.token.is_none(), "Token already created");
        chain.token = Some(token);
        Ok(self.chains.insert(&chain_id, chain)?)
    }

    pub(crate) async fn register_miner(&mut self, owner: Account) -> Result<(), ProxyError> {
        assert!(
            self.miners()
                .await?
                .iter()
                .filter(|miner| miner.owner == owner.owner)
                .collect::<Vec<_>>()
                .len()
                == 0,
            "Already registered"
        );
        Ok(self.miners.insert(&owner, Miner { owner })?)
    }

    pub(crate) fn deregister_miner(&mut self, owner: Account) -> Result<(), ProxyError> {
        Ok(self.miners.remove(&owner)?)
    }
}
