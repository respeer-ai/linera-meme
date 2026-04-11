use std::{cell::RefCell, rc::Rc};

use super::errors::StateError;
use crate::{interfaces::state::StateInterface, state::AmsState};
use abi::ams::{InstantiationArgument, Metadata};
use async_trait::async_trait;

use linera_sdk::linera_base_types::{Account, ApplicationId};

pub struct StateAdapter {
    state: Rc<RefCell<AmsState>>,
}

impl StateAdapter {
    pub fn new(state: Rc<RefCell<AmsState>>) -> Self {
        Self { state }
    }
}

#[async_trait(?Send)]
impl StateInterface for StateAdapter {
    type Error = StateError;

    fn instantiate(&mut self, owner: Account, argument: InstantiationArgument) {
        self.state.borrow_mut().instantiate(owner, argument)
    }

    async fn add_application_type(
        &mut self,
        owner: Account,
        application_type: String,
    ) -> Result<(), Self::Error> {
        self.state
            .borrow_mut()
            .add_application_type(owner, application_type)
            .await
    }

    fn register_application(&mut self, application: Metadata) -> Result<(), Self::Error> {
        self.state.borrow_mut().register_application(application)
    }

    async fn claim_application(
        &mut self,
        owner: Account,
        application_id: ApplicationId,
    ) -> Result<(), Self::Error> {
        self.state
            .borrow_mut()
            .claim_application(owner, application_id)
            .await
    }

    async fn update_application(
        &mut self,
        owner: Account,
        application_id: ApplicationId,
        metadata: Metadata,
    ) -> Result<(), Self::Error> {
        self.state
            .borrow_mut()
            .update_application(owner, application_id, metadata)
            .await
    }
}
