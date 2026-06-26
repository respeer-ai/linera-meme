use std::{cell::RefCell, rc::Rc};

use async_trait::async_trait;
use linera_sdk::linera_base_types::{Account, ApplicationId};

use crate::{interfaces::state::StateInterface, state::State, state_key::StateKey};

pub struct StateAdapter {
    state: Rc<RefCell<State>>,
}

impl StateAdapter {
    pub fn new(state: Rc<RefCell<State>>) -> Self {
        Self { state }
    }
}

#[async_trait(?Send)]
impl StateInterface for StateAdapter {
    type Error = <State as StateInterface>::Error;

    async fn operator(&mut self) -> Result<Account, Self::Error> {
        self.state.borrow_mut().operator().await
    }

    async fn initialize_operator(&mut self, operator: Account) -> Result<(), Self::Error> {
        self.state.borrow_mut().initialize_operator(operator).await
    }

    async fn create_namespace(
        &mut self,
        namespace: u8,
        application_id: ApplicationId,
    ) -> Result<(), Self::Error> {
        self.state
            .borrow_mut()
            .create_namespace(namespace, application_id)
            .await
    }

    async fn freeze_namespace(&mut self) -> Result<(), Self::Error> {
        self.state.borrow_mut().freeze_namespace().await
    }

    async fn unfreeze_namespace(&mut self) -> Result<(), Self::Error> {
        self.state.borrow_mut().unfreeze_namespace().await
    }

    async fn handoff(
        &mut self,
        namespace: u8,
        application_id: ApplicationId,
        new_application_id: ApplicationId,
    ) -> Result<(), Self::Error> {
        self.state
            .borrow_mut()
            .handoff(namespace, application_id, new_application_id)
            .await
    }

    async fn set_operator(&mut self, new_operator: Account) -> Result<(), Self::Error> {
        self.state.borrow_mut().set_operator(new_operator).await
    }

    async fn application_slot(
        &mut self,
        namespace: u8,
        application_id: ApplicationId,
    ) -> Result<u8, Self::Error> {
        self.state
            .borrow_mut()
            .application_slot(namespace, application_id)
            .await
    }

    async fn read(&mut self, key: StateKey) -> Result<Option<Vec<u8>>, Self::Error> {
        self.state.borrow_mut().read(key).await
    }

    async fn write(&mut self, key: StateKey, value: Vec<u8>) -> Result<(), Self::Error> {
        self.state.borrow_mut().write(key, value).await
    }

    async fn delete(&mut self, key: StateKey) -> Result<(), Self::Error> {
        self.state.borrow_mut().delete(key).await
    }

    async fn batch_read(
        &mut self,
        keys: Vec<StateKey>,
    ) -> Result<Vec<Option<Vec<u8>>>, Self::Error> {
        self.state.borrow_mut().batch_read(keys).await
    }

    async fn batch_write(&mut self, writes: Vec<(StateKey, Vec<u8>)>) -> Result<(), Self::Error> {
        self.state.borrow_mut().batch_write(writes).await
    }

    async fn batch_delete(&mut self, keys: Vec<StateKey>) -> Result<(), Self::Error> {
        self.state.borrow_mut().batch_delete(keys).await
    }
}
