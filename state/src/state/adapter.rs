use std::{cell::RefCell, rc::Rc};

use async_trait::async_trait;
use linera_sdk::linera_base_types::{Account, ApplicationId};

use crate::{interfaces::state::StateInterface, state::State};

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

    async fn initialize_operator(&mut self) -> Result<(), Self::Error> {
        self.state.borrow_mut().initialize_operator().await
    }

    async fn create_namespace(&mut self, namespace: u8) -> Result<(), Self::Error> {
        self.state.borrow_mut().create_namespace(namespace).await
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
        new_application_id: ApplicationId,
    ) -> Result<(), Self::Error> {
        self.state
            .borrow_mut()
            .handoff(namespace, new_application_id)
            .await
    }

    async fn set_operator(&mut self, new_operator: Account) -> Result<(), Self::Error> {
        self.state.borrow_mut().set_operator(new_operator).await
    }

    async fn batch_read(
        &mut self,
        namespace: u8,
        keys: Vec<Vec<u8>>,
    ) -> Result<Vec<Option<Vec<u8>>>, Self::Error> {
        self.state.borrow_mut().batch_read(namespace, keys).await
    }

    async fn batch_write(
        &mut self,
        namespace: u8,
        writes: Vec<(Vec<u8>, Option<Vec<u8>>)>,
    ) -> Result<(), Self::Error> {
        self.state.borrow_mut().batch_write(namespace, writes).await
    }
}
