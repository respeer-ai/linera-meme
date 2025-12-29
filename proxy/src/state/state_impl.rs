use crate::{
    interfaces::state::StateInterface,
    state::{errors::StateError, ProxyState},
};
use abi::{
    approval::Approval,
    proxy::{Chain, GenesisMiner, InstantiationArgument, Miner},
};
use async_trait::async_trait;
use linera_sdk::linera_base_types::{
    Account, AccountOwner, ApplicationId, ChainId, ModuleId, Timestamp,
};

#[async_trait(?Send)]
impl StateInterface for ProxyState {
    type Error = StateError;

    async fn instantiate(
        &mut self,
        argument: InstantiationArgument,
        owners: Vec<Account>,
    ) -> Result<(), StateError> {
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

    async fn initial_approval(&self) -> Result<Approval, StateError> {
        let operators = self.operators.count().await?;
        Ok(Approval::new(std::cmp::max(operators * 2 / 3, 1)))
    }

    async fn add_genesis_miner(&mut self, owner: Account) -> Result<(), StateError> {
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

    async fn genesis_miners(&self) -> Result<Vec<Account>, StateError> {
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

    async fn is_genesis_miner(&self, owner: Account) -> Result<bool, StateError> {
        Ok(self.genesis_miners.contains_key(&owner).await?)
    }

    async fn genesis_miner_owners(&self) -> Result<Vec<AccountOwner>, StateError> {
        Ok(self
            .genesis_miners()
            .await?
            .into_iter()
            .map(|owner| owner.owner)
            .collect())
    }

    async fn miners(&self) -> Result<Vec<Account>, StateError> {
        Ok(self.miners.indices().await?)
    }

    async fn miner_owners(&self) -> Result<Vec<AccountOwner>, StateError> {
        Ok(self
            .miners()
            .await?
            .into_iter()
            .map(|owner| owner.owner)
            .collect())
    }

    async fn validate_operator(&self, owner: Account) -> Result<(), StateError> {
        let approval = self.operators.get(&owner).await?.unwrap();
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
        Ok(self.operators.insert(&owner, approval)?)
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
        let mut chain = self.chains.get(&chain_id).await?.unwrap();
        assert!(chain.token.is_none(), "Token already created");
        chain.token = Some(token);
        Ok(self.chains.insert(&chain_id, chain)?)
    }

    async fn register_miner(&mut self, owner: Account) -> Result<(), StateError> {
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

    fn deregister_miner(&mut self, owner: Account) -> Result<(), StateError> {
        Ok(self.miners.remove(&owner)?)
    }
}
