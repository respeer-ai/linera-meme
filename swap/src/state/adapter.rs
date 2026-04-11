use std::{cell::RefCell, rc::Rc};

use super::errors::StateError;
use crate::{interfaces::state::StateInterface, state::SwapState};
use abi::swap::{
    router::{InstantiationArgument, Pool},
    transaction::Transaction,
};
use async_trait::async_trait;

use linera_sdk::linera_base_types::{Account, Amount, ApplicationId, ChainId, ModuleId, Timestamp};

pub struct StateAdapter {
    state: Rc<RefCell<SwapState>>,
}

impl StateAdapter {
    pub fn new(state: Rc<RefCell<SwapState>>) -> Self {
        Self { state }
    }
}

#[async_trait(?Send)]
impl StateInterface for StateAdapter {
    type Error = StateError;

    fn instantiate(&mut self, owner: Account, argument: InstantiationArgument) {
        self.state.borrow_mut().instantiate(owner, argument)
    }

    async fn get_pool(
        &self,
        token_0: ApplicationId,
        token_1: Option<ApplicationId>,
    ) -> Result<Option<Pool>, Self::Error> {
        self.state.borrow().get_pool(token_0, token_1).await
    }

    async fn get_pool_exchangable(
        &self,
        token_0: ApplicationId,
        token_1: Option<ApplicationId>,
    ) -> Result<Option<Pool>, Self::Error> {
        self.state
            .borrow()
            .get_pool_exchangable(token_0, token_1)
            .await
    }

    fn pool_bytecode_id(&self) -> ModuleId {
        self.state.borrow().pool_bytecode_id()
    }

    async fn create_pool(
        &mut self,
        creator: Account,
        token_0: ApplicationId,
        token_1: Option<ApplicationId>,
        pool_application: Account,
        timestamp: Timestamp,
    ) -> Result<(), Self::Error> {
        self.state
            .borrow_mut()
            .create_pool(creator, token_0, token_1, pool_application, timestamp)
            .await
    }

    fn create_pool_chain(&mut self, chain_id: ChainId) -> Result<(), Self::Error> {
        self.state.borrow_mut().create_pool_chain(chain_id)
    }

    async fn is_pool_chain(&self, chain_id: ChainId) -> Result<bool, Self::Error> {
        Ok(self
            .state
            .borrow()
            .pool_chains
            .get(&chain_id)
            .await?
            .unwrap_or(false))
    }

    async fn mark_user_pool_created(
        &mut self,
        pool_application: Account,
    ) -> Result<bool, Self::Error> {
        let already_processed = self
            .state
            .borrow()
            .processed_user_pool_creations
            .get(&pool_application)
            .await?
            .unwrap_or(false);
        if already_processed {
            return Ok(false);
        }
        self.state
            .borrow_mut()
            .processed_user_pool_creations
            .insert(&pool_application, true)?;
        Ok(true)
    }

    async fn update_pool(
        &mut self,
        token_0: ApplicationId,
        token_1: Option<ApplicationId>,
        transaction: Transaction,
        token_0_price: Amount,
        token_1_price: Amount,
        reserve_0: Amount,
        reserve_1: Amount,
    ) -> Result<(), Self::Error> {
        self.state
            .borrow_mut()
            .update_pool(
                token_0,
                token_1,
                transaction,
                token_0_price,
                token_1_price,
                reserve_0,
                reserve_1,
            )
            .await
    }
}
