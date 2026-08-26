use std::{cell::RefCell, rc::Rc};

use abi::{
    approval::Approval,
    proxy::{state_v1::StateInstantiationArgument, Chain, InitializeArgument, Miner},
};
use async_trait::async_trait;
use linera_sdk::linera_base_types::{
    Account, AccountOwner, ApplicationId, ChainId, ModuleId, Timestamp,
};

use crate::{interfaces::state::StateInterface, state::ProxyState};

pub struct StateAdapter {
    state: Rc<RefCell<ProxyState>>,
}

impl StateAdapter {
    pub fn new(state: Rc<RefCell<ProxyState>>) -> Self {
        Self { state }
    }
}

#[async_trait(?Send)]
impl StateInterface for StateAdapter {
    type Error = <ProxyState as StateInterface>::Error;

    fn instantiate(&mut self, argument: StateInstantiationArgument) -> Result<(), Self::Error> {
        self.state.borrow_mut().instantiate(argument)?;
        Ok(())
    }

    async fn initialize(&mut self, argument: InitializeArgument) -> Result<(), Self::Error> {
        self.state.borrow_mut().initialize(argument).await
    }

    async fn business_application_id(&mut self) -> Result<ApplicationId, Self::Error> {
        self.state.borrow_mut().business_application_id().await
    }

    async fn handoff(
        &mut self,
        new_business_application_id: ApplicationId,
    ) -> Result<(), Self::Error> {
        self.state
            .borrow_mut()
            .handoff(new_business_application_id)
            .await
    }

    async fn operator(&mut self) -> Result<Account, Self::Error> {
        self.state.borrow_mut().operator().await
    }

    async fn set_operator(&mut self, new_operator: Account) -> Result<(), Self::Error> {
        self.state.borrow_mut().set_operator(new_operator).await
    }

    async fn initial_approval(&self) -> Result<Approval, Self::Error> {
        self.state.borrow().initial_approval().await
    }

    async fn add_genesis_miner(&mut self, owner: Account) -> Result<(), Self::Error> {
        self.state.borrow_mut().add_genesis_miner(owner).await
    }

    async fn approve_add_genesis_miner(
        &mut self,
        owner: Account,
        operator: Account,
    ) -> Result<(), Self::Error> {
        self.state
            .borrow_mut()
            .approve_add_genesis_miner(owner, operator)
            .await
    }

    async fn genesis_miners(&self) -> Result<Vec<Miner>, Self::Error> {
        self.state.borrow().genesis_miners().await
    }

    async fn is_genesis_miner(&self, owner: Account) -> Result<bool, Self::Error> {
        self.state.borrow().is_genesis_miner(owner).await
    }

    async fn genesis_miner_owners(&self) -> Result<Vec<AccountOwner>, Self::Error> {
        self.state.borrow().genesis_miner_owners().await
    }

    async fn miners(&self) -> Result<Vec<Miner>, Self::Error> {
        self.state.borrow().miners().await
    }

    async fn miner_owners(&self) -> Result<Vec<AccountOwner>, Self::Error> {
        self.state.borrow().miner_owners().await
    }

    async fn validate_operator(&self, owner: Account) -> Result<(), Self::Error> {
        self.state.borrow().validate_operator(owner).await
    }

    async fn add_operator(&mut self, owner: Account) -> Result<(), Self::Error> {
        self.state.borrow_mut().add_operator(owner).await
    }

    async fn approve_add_operator(
        &mut self,
        owner: Account,
        operator: Account,
    ) -> Result<(), Self::Error> {
        self.state
            .borrow_mut()
            .approve_add_operator(owner, operator)
            .await
    }

    async fn ban_operator(&mut self, owner: Account) -> Result<(), Self::Error> {
        self.state.borrow_mut().ban_operator(owner).await
    }

    async fn approve_ban_operator(
        &mut self,
        owner: Account,
        operator: Account,
    ) -> Result<(), Self::Error> {
        self.state
            .borrow_mut()
            .approve_ban_operator(owner, operator)
            .await
    }

    async fn remove_genesis_miner(&mut self, owner: Account) -> Result<(), Self::Error> {
        self.state.borrow_mut().remove_genesis_miner(owner).await
    }

    async fn approve_remove_genesis_miner(
        &mut self,
        owner: Account,
        operator: Account,
    ) -> Result<(), Self::Error> {
        self.state
            .borrow_mut()
            .approve_remove_genesis_miner(owner, operator)
            .await
    }

    fn meme_bytecode_id(&self) -> ModuleId {
        self.state.borrow().meme_bytecode_id()
    }

    async fn set_meme_bytecode_ids(
        &mut self,
        business_bytecode_id: ModuleId,
        state_bytecode_id: ModuleId,
    ) -> Result<(), Self::Error> {
        self.state
            .borrow_mut()
            .set_meme_bytecode_ids(business_bytecode_id, state_bytecode_id)
            .await
    }

    async fn meme_state_bytecode_ids(&self) -> Result<Vec<(u16, ModuleId)>, Self::Error> {
        self.state.borrow().meme_state_bytecode_ids().await
    }

    fn swap_application_id(&self) -> ApplicationId {
        self.state.borrow().swap_application_id()
    }

    fn create_chain(&mut self, chain_id: ChainId, timestamp: Timestamp) -> Result<(), Self::Error> {
        self.state.borrow_mut().create_chain(chain_id, timestamp)
    }

    async fn create_chain_token(
        &mut self,
        chain_id: ChainId,
        token: ApplicationId,
    ) -> Result<(), Self::Error> {
        self.state
            .borrow_mut()
            .create_chain_token(chain_id, token)
            .await
    }

    async fn register_miner(&mut self, owner: Account, now: Timestamp) -> Result<(), Self::Error> {
        self.state.borrow_mut().register_miner(owner, now).await
    }

    async fn deregister_miner(&mut self, owner: Account) -> Result<(), Self::Error> {
        self.state.borrow_mut().deregister_miner(owner).await
    }

    async fn get_miner_with_account_owner(
        &self,
        owner: AccountOwner,
    ) -> Result<Miner, Self::Error> {
        self.state.borrow().get_miner_with_account_owner(owner).await
    }

    async fn chain(&self, chain_id: ChainId) -> Result<Option<Chain>, Self::Error> {
        self.state.borrow().chain(chain_id).await
    }

    async fn chains(&self, created_after: Option<Timestamp>) -> Result<Vec<Chain>, Self::Error> {
        self.state.borrow().chains(created_after).await
    }

    async fn chain_by_token(&self, token: ApplicationId) -> Result<Option<Chain>, Self::Error> {
        self.state.borrow().chain_by_token(token).await
    }
}
