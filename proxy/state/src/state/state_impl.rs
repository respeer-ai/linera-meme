use crate::{
    interfaces::state::StateInterface,
    state::{errors::StateError, ProxyState},
};
use abi::{
    approval::Approval,
    proxy::{state_v1::StateInstantiationArgument, Chain, GenesisMiner, InitializeArgument, Miner},
};
use async_trait::async_trait;
use linera_sdk::linera_base_types::{
    Account, AccountOwner, ApplicationId, ChainId, ModuleId, Timestamp,
};

#[async_trait(?Send)]
impl StateInterface for ProxyState {
    type Error = StateError;

    fn instantiate(&mut self, argument: StateInstantiationArgument) -> Result<(), StateError> {
        self.business_application_id
            .set(Some(argument.business_application_id));
        self.operator.set(argument.operator);

        Ok(())
    }

    async fn initialize(&mut self, argument: InitializeArgument) -> Result<(), StateError> {
        if self.meme_bytecode_id.get().is_some() {
            // Idempotent: already initialized.
            return Ok(());
        }

        self.meme_bytecode_id.set(Some(argument.meme_bytecode_id));
        for state_bytecode_id in &argument.meme_state_bytecode_ids {
            self.meme_state_bytecode_ids.insert(
                &state_bytecode_id.version,
                state_bytecode_id.module_id,
            )?;
        }

        for operator in &argument.initial_operators {
            let mut approval = Approval::new(1);
            approval.approve(*operator);
            self.operators.insert(operator, approval)?;
        }

        self.swap_application_id
            .set(Some(argument.swap_application_id));

        for owner in &argument.genesis_miner_owners {
            let mut approval = Approval::new(1);
            approval.approve(*owner);
            self.genesis_miners.insert(
                owner,
                GenesisMiner {
                    owner: *owner,
                    approval: approval.clone(),
                },
            )?;
        }

        Ok(())
    }

    async fn business_application_id(&mut self) -> Result<ApplicationId, StateError> {
        self.business_application_id
            .get()
            .ok_or(StateError::BusinessApplicationIdNotInitialized)
    }

    async fn handoff(
        &mut self,
        new_business_application_id: ApplicationId,
    ) -> Result<(), StateError> {
        self.business_application_id
            .set(Some(new_business_application_id));
        Ok(())
    }

    async fn operator(&mut self) -> Result<Account, StateError> {
        self.operator
            .get()
            .ok_or(StateError::OperatorNotInitialized)
    }

    async fn set_operator(&mut self, new_operator: Account) -> Result<(), StateError> {
        self.operator.set(Some(new_operator));
        Ok(())
    }

    async fn initial_approval(&self) -> Result<Approval, StateError> {
        let operators = self.operators.count().await?;
        Ok(Approval::new(std::cmp::max(operators * 2 / 3, 1)))
    }

    async fn add_genesis_miner(&mut self, owner: Account) -> Result<(), StateError> {
        // TODO: if AccountOwner exists, reject
        assert!(
            !self.genesis_miners.contains_key(&owner).await?,
            "Already exists",
        );
        let approval = self.initial_approval().await?;
        Ok(self
            .genesis_miners
            .insert(&owner, GenesisMiner { owner, approval })?)
    }

    async fn approve_add_genesis_miner(
        &mut self,
        owner: Account,
        operator: Account,
    ) -> Result<(), StateError> {
        let mut miner = self.genesis_miners.get(&owner).await?.unwrap();
        assert!(!miner.approval.voted(operator), "Already voted");
        miner.approval.approve(operator);
        Ok(self.genesis_miners.insert(&owner, miner)?)
    }

    async fn genesis_miners(&self) -> Result<Vec<Miner>, StateError> {
        let mut miners = Vec::new();
        self.genesis_miners
            .for_each_index_value(|owner, miner| {
                let approval = miner.into_owned().approval;
                if approval.approved() {
                    miners.push(Miner {
                        owner,
                        registered_at: 0.into(),
                    });
                }
                Ok(())
            })
            .await?;
        Ok(miners)
    }

    async fn is_genesis_miner(&self, owner: Account) -> Result<bool, StateError> {
        Ok(self.genesis_miners.contains_key(&owner).await?)
    }

    async fn genesis_miner_owners(&self) -> Result<Vec<AccountOwner>, StateError> {
        Ok(self
            .genesis_miners()
            .await?
            .into_iter()
            .map(|miner| miner.owner.owner)
            .collect())
    }

    async fn miners(&self) -> Result<Vec<Miner>, StateError> {
        let genesis_miners = self.genesis_miners().await?;

        Ok(self
            .miners
            .index_values()
            .await?
            .into_iter()
            .map(|(_, miner)| miner)
            .chain(genesis_miners.into_iter())
            .collect())
    }

    async fn miner_owners(&self) -> Result<Vec<AccountOwner>, StateError> {
        Ok(self
            .miners()
            .await?
            .into_iter()
            .map(|miner| miner.owner.owner)
            .collect())
    }

    async fn validate_operator(&self, owner: Account) -> Result<(), StateError> {
        let Some(approval) = self.operators.get(&owner).await? else {
            panic!("Invalid operator");
        };
        assert!(approval.approved(), "Invalid operator");
        Ok(())
    }

    async fn add_operator(&mut self, owner: Account) -> Result<(), StateError> {
        assert!(
            !self.operators.contains_key(&owner).await?,
            "Already exists",
        );
        let approval = self.initial_approval().await?;
        Ok(self.operators.insert(&owner, approval)?)
    }

    // Owner is approved operator, operator is voter
    async fn approve_add_operator(
        &mut self,
        owner: Account,
        operator: Account,
    ) -> Result<(), StateError> {
        let mut approval = self.operators.get(&owner).await?.unwrap();
        assert!(!approval.voted(operator), "Already voted");
        approval.approve(operator);
        Ok(self.operators.insert(&owner, approval)?)
    }

    async fn ban_operator(&mut self, owner: Account) -> Result<(), StateError> {
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
    async fn approve_ban_operator(
        &mut self,
        owner: Account,
        operator: Account,
    ) -> Result<(), StateError> {
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
        Ok(self.banning_operators.insert(&owner, approval)?)
    }

    async fn remove_genesis_miner(&mut self, owner: Account) -> Result<(), StateError> {
        if self.removing_genesis_miners.contains_key(&owner).await? {
            return Ok(());
        }
        if !self.genesis_miners.contains_key(&owner).await? {
            return Err(StateError::NotExists);
        }
        let approval = self.initial_approval().await?;
        Ok(self.removing_genesis_miners.insert(&owner, approval)?)
    }

    async fn approve_remove_genesis_miner(
        &mut self,
        owner: Account,
        operator: Account,
    ) -> Result<(), StateError> {
        let mut approval = self.removing_genesis_miners.get(&owner).await?.unwrap();
        assert!(!approval.voted(operator), "Already voted");
        approval.approve(operator);
        if approval.approved() {
            self.removing_genesis_miners.remove(&owner)?;
            return Ok(self.genesis_miners.remove(&owner)?);
        }
        Ok(self.removing_genesis_miners.insert(&owner, approval)?)
    }

    fn meme_bytecode_id(&self) -> ModuleId {
        self.meme_bytecode_id.get().unwrap()
    }

    async fn set_meme_bytecode_ids(
        &mut self,
        business_bytecode_id: ModuleId,
        state_bytecode_id: ModuleId,
    ) -> Result<(), StateError> {
        self.meme_bytecode_id.set(Some(business_bytecode_id));

        let max_version = self
            .meme_state_bytecode_ids
            .index_values()
            .await?
            .into_iter()
            .map(|(version, _)| version)
            .max()
            .unwrap_or(0);
        let next_version = max_version + 1;

        self.meme_state_bytecode_ids
            .insert(&next_version, state_bytecode_id)?;
        Ok(())
    }

    async fn meme_state_bytecode_ids(&self) -> Result<Vec<(u16, ModuleId)>, StateError> {
        let mut ids = self.meme_state_bytecode_ids.index_values().await?;
        ids.sort_by_key(|(version, _)| *version);
        Ok(ids)
    }

    fn swap_application_id(&self) -> ApplicationId {
        self.swap_application_id.get().unwrap()
    }

    fn create_chain(&mut self, chain_id: ChainId, timestamp: Timestamp) -> Result<(), StateError> {
        Ok(self.chains.insert(
            &chain_id,
            Chain {
                chain_id,
                created_at: timestamp,
                token: None,
            },
        )?)
    }

    async fn create_chain_token(
        &mut self,
        chain_id: ChainId,
        token: ApplicationId,
    ) -> Result<(), StateError> {
        let Some(mut chain) = self.chains.get(&chain_id).await? else {
            return Ok(());
        };
        if chain.token == Some(token) {
            return Ok(());
        }
        assert!(chain.token.is_none(), "Token already created");
        chain.token = Some(token);
        Ok(self.chains.insert(&chain_id, chain)?)
    }

    async fn register_miner(&mut self, owner: Account, now: Timestamp) -> Result<(), StateError> {
        assert!(
            self.miners()
                .await?
                .iter()
                .filter(|miner| miner.owner.owner == owner.owner)
                .collect::<Vec<_>>()
                .len()
                == 0,
            "Already registered"
        );
        Ok(self.miners.insert(
            &owner,
            Miner {
                owner,
                registered_at: now,
            },
        )?)
    }

    async fn deregister_miner(&mut self, owner: Account) -> Result<(), StateError> {
        if !self.miners.contains_key(&owner).await? {
            return Err(StateError::NotExists);
        }
        Ok(self.miners.remove(&owner)?)
    }

    async fn get_miner_with_account_owner(
        &self,
        owner: AccountOwner,
    ) -> Result<Miner, StateError> {
        log::info!("Miners {:?}, owner {}", self.miners().await?, owner);

        match self
            .miners()
            .await?
            .iter()
            .filter(|miner| miner.owner.owner == owner)
            .next()
        {
            Some(miner) => Ok(miner.clone()),
            _ => Err(StateError::NotExists),
        }
    }

    async fn chain(&self, chain_id: ChainId) -> Result<Option<Chain>, StateError> {
        Ok(self.chains.get(&chain_id).await?)
    }

    async fn chains(&self, created_after: Option<Timestamp>) -> Result<Vec<Chain>, StateError> {
        let mut chains = Vec::new();
        self.chains
            .for_each_index_value(|_chain_id, chain| {
                if created_after.map_or(true, |ts| chain.created_at >= ts) {
                    chains.push(chain.into_owned());
                }
                Ok(())
            })
            .await?;
        Ok(chains)
    }

    async fn chain_by_token(&self, token: ApplicationId) -> Result<Option<Chain>, StateError> {
        let mut found = None;
        self.chains
            .for_each_index_value(|_chain_id, chain| {
                if chain.token == Some(token) {
                    found = Some(chain.into_owned());
                }
                Ok(())
            })
            .await?;
        Ok(found)
    }
}
