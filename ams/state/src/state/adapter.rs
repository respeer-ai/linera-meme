use std::{cell::RefCell, rc::Rc};

use abi::ams::{abi::Metadata, state_v1::StateInstantiationArgument};
use async_trait::async_trait;
use linera_sdk::linera_base_types::{Account, ApplicationId};

use crate::{interfaces::state::StateInterface, state::AmsState};

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
    type Error = <AmsState as StateInterface>::Error;

    fn instantiate(&mut self, argument: StateInstantiationArgument) {
        self.state.borrow_mut().instantiate(argument);
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

    async fn add_application_type(&mut self, application_type: String) -> Result<(), Self::Error> {
        self.state
            .borrow_mut()
            .add_application_type(application_type)
            .await
    }

    async fn application_types(&mut self) -> Result<Vec<String>, Self::Error> {
        self.state.borrow_mut().application_types().await
    }

    async fn register_application(&mut self, metadata: Metadata) -> Result<(), Self::Error> {
        self.state.borrow_mut().register_application(metadata).await
    }

    async fn claim_application(
        &mut self,
        application_id: ApplicationId,
        creator: Account,
    ) -> Result<(), Self::Error> {
        self.state
            .borrow_mut()
            .claim_application(application_id, creator)
            .await
    }

    async fn update_application(
        &mut self,
        application_id: ApplicationId,
        metadata: Metadata,
    ) -> Result<(), Self::Error> {
        self.state
            .borrow_mut()
            .update_application(application_id, metadata)
            .await
    }

    async fn application(
        &mut self,
        application_id: ApplicationId,
    ) -> Result<Option<Metadata>, Self::Error> {
        self.state.borrow_mut().application(application_id).await
    }
}
