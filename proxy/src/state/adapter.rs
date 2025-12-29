use crate::{
    interfaces::state::StateInterface,
    state::{errors::StateError, ProxyState},
};
use abi::{approval::Approval, proxy::InstantiationArgument};
use async_trait::async_trait;
use linera_sdk::linera_base_types::{
    Account, AccountOwner, ApplicationId, ChainId, ModuleId, Timestamp,
};
use std::{cell::RefCell, rc::Rc};

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
    type Error = StateError;

    async fn instantiate(
        &mut self,
        argument: InstantiationArgument,
        owners: Vec<Account>,
    ) -> Result<(), StateError> {
        self.state.borrow_mut().instantiate(argument, owners).await
    }

    async fn initial_approval(&self) -> Result<Approval, StateError> {
        self.state.borrow().initial_approval().await
    }

    async fn add_genesis_miner(&mut self, owner: Account) -> Result<(), StateError> {
        self.state.borrow_mut().add_genesis_miner(owner).await
    }

    async fn approve_add_genesis_miner(
        &mut self,
        owner: Account,
        operator: Account,
    ) -> Result<(), StateError> {
        self.state
            .borrow_mut()
            .approve_add_genesis_miner(owner, operator)
            .await
    }

    async fn genesis_miners(&self) -> Result<Vec<Account>, StateError> {
        self.state.borrow().genesis_miners().await
    }

    async fn is_genesis_miner(&self, owner: Account) -> Result<bool, StateError> {
        self.state.borrow().is_genesis_miner(owner).await
    }

    async fn genesis_miner_owners(&self) -> Result<Vec<AccountOwner>, StateError> {
        self.state.borrow().genesis_miner_owners().await
    }

    async fn miners(&self) -> Result<Vec<Account>, StateError> {
        self.state.borrow().miners().await
    }

    async fn miner_owners(&self) -> Result<Vec<AccountOwner>, StateError> {
        self.state.borrow().miner_owners().await
    }

    async fn validate_operator(&self, owner: Account) -> Result<(), StateError> {
        self.state.borrow().validate_operator(owner).await
    }

    async fn add_operator(&mut self, owner: Account) -> Result<(), StateError> {
        self.state.borrow_mut().add_operator(owner).await
    }

    // Owner is approved operator, operator is voter
    async fn approve_add_operator(
        &mut self,
        owner: Account,
        operator: Account,
    ) -> Result<(), StateError> {
        self.state
            .borrow_mut()
            .approve_add_operator(owner, operator)
            .await
    }

    async fn ban_operator(&mut self, owner: Account) -> Result<(), StateError> {
        self.state.borrow_mut().ban_operator(owner).await
    }

    // Owner is approved operator, operator is voter
    async fn approve_ban_operator(
        &mut self,
        owner: Account,
        operator: Account,
    ) -> Result<(), StateError> {
        self.state
            .borrow_mut()
            .approve_ban_operator(owner, operator)
            .await
    }

    async fn remove_genesis_miner(&mut self, owner: Account) -> Result<(), StateError> {
        self.state.borrow_mut().remove_genesis_miner(owner).await
    }

    async fn approve_remove_genesis_miner(
        &mut self,
        owner: Account,
        operator: Account,
    ) -> Result<(), StateError> {
        self.state
            .borrow_mut()
            .approve_remove_genesis_miner(owner, operator)
            .await
    }

    fn meme_bytecode_id(&self) -> ModuleId {
        self.state.borrow().meme_bytecode_id()
    }

    fn swap_application_id(&self) -> ApplicationId {
        self.state.borrow().swap_application_id()
    }

    fn create_chain(&mut self, chain_id: ChainId, timestamp: Timestamp) -> Result<(), StateError> {
        self.state.borrow_mut().create_chain(chain_id, timestamp)
    }

    async fn create_chain_token(
        &mut self,
        chain_id: ChainId,
        token: ApplicationId,
    ) -> Result<(), StateError> {
        self.state
            .borrow_mut()
            .create_chain_token(chain_id, token)
            .await
    }

    async fn register_miner(&mut self, owner: Account) -> Result<(), StateError> {
        self.state.borrow_mut().register_miner(owner).await
    }

    fn deregister_miner(&mut self, owner: Account) -> Result<(), StateError> {
        self.state.borrow_mut().deregister_miner(owner)
    }
}
