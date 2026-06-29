use std::{cell::RefCell, rc::Rc};

use crate::{interfaces::state::StateInterface, state::AmsState};
use abi::{
    ams::{
        abi::Metadata,
        state_v1::{
            AmsStateAbi as AmsStateV1Abi, AmsStateOperation as AmsStateV1Operation,
            AmsStateResponse as AmsStateV1Response,
        },
    },
    application_base_state::{LocalStateInterface, PublicStateBaseInterface},
};
use async_trait::async_trait;
use linera_sdk::linera_base_types::{Account, ApplicationId};
use runtime::interfaces::contract::ContractRuntimeContext;

use super::StateError;

pub struct ContractStateAdapter<R: ContractRuntimeContext> {
    runtime_context: Rc<RefCell<R>>,
    state: Rc<RefCell<AmsState>>,
}

impl<R: ContractRuntimeContext> ContractStateAdapter<R> {
    pub fn new(runtime_context: Rc<RefCell<R>>, state: Rc<RefCell<AmsState>>) -> Self {
        Self {
            runtime_context,
            state,
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext> PublicStateBaseInterface for ContractStateAdapter<R> {
    type Error = StateError;
    type BootstrapArgument = ();

    async fn append_state(
        &mut self,
        state_application_id: ApplicationId,
    ) -> Result<(), Self::Error> {
        self.state
            .borrow_mut()
            .append_state(state_application_id)
            .await
    }

    async fn bootstrap(&mut self, _argument: ()) -> Result<(), Self::Error> {
        let state_application_id = self.state.borrow().latest_state_application().await?;
        let response = self.runtime_context.borrow_mut().call_application(
            state_application_id.with_abi::<AmsStateV1Abi>(),
            &AmsStateV1Operation::Bootstrap,
        );
        match response {
            AmsStateV1Response::Ok => Ok(()),
            _ => Err(StateError::InvalidStateResponse),
        }
    }

    async fn handoff(
        &mut self,
        new_business_application_id: ApplicationId,
    ) -> Result<(), Self::Error> {
        for (version, state_application_id) in self.state.borrow().state_applications().await? {
            let response = match version {
                1 => self.runtime_context.borrow_mut().call_application(
                    state_application_id.with_abi::<AmsStateV1Abi>(),
                    &AmsStateV1Operation::Handoff {
                        new_business_application_id,
                    },
                ),
                _ => return Err(StateError::InvalidStateVersion),
            };
            match response {
                AmsStateV1Response::Ok => {}
                _ => return Err(StateError::InvalidStateResponse),
            }
        }
        Ok(())
    }

    async fn set_operator(&mut self, new_operator: Account) -> Result<(), Self::Error> {
        let state_application_id = self.state.borrow().latest_state_application().await?;
        let response = self.runtime_context.borrow_mut().call_application(
            state_application_id.with_abi::<AmsStateV1Abi>(),
            &AmsStateV1Operation::SetOperator { new_operator },
        );
        match response {
            AmsStateV1Response::Ok => Ok(()),
            _ => Err(StateError::InvalidStateResponse),
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext> StateInterface for ContractStateAdapter<R> {
    type Error = StateError;

    async fn add_application_type(
        &mut self,
        owner: Account,
        application_type: String,
    ) -> Result<(), Self::Error> {
        let state_application_id = self.state.borrow().state_application(1).await?;
        let response = self.runtime_context.borrow_mut().call_application(
            state_application_id.with_abi::<AmsStateV1Abi>(),
            &AmsStateV1Operation::AddApplicationType {
                owner,
                application_type,
            },
        );
        match response {
            AmsStateV1Response::Ok => Ok(()),
            _ => Err(StateError::InvalidStateResponse),
        }
    }

    async fn register_application(&mut self, application: Metadata) -> Result<(), Self::Error> {
        let state_application_id = self.state.borrow().state_application(1).await?;
        let response = self.runtime_context.borrow_mut().call_application(
            state_application_id.with_abi::<AmsStateV1Abi>(),
            &AmsStateV1Operation::RegisterApplication {
                metadata: application,
            },
        );
        match response {
            AmsStateV1Response::Ok => Ok(()),
            _ => Err(StateError::InvalidStateResponse),
        }
    }

    async fn claim_application(
        &mut self,
        owner: Account,
        application_id: ApplicationId,
    ) -> Result<(), Self::Error> {
        let state_application_id = self.state.borrow().state_application(1).await?;
        let response = self.runtime_context.borrow_mut().call_application(
            state_application_id.with_abi::<AmsStateV1Abi>(),
            &AmsStateV1Operation::ClaimApplication {
                owner,
                application_id,
            },
        );
        match response {
            AmsStateV1Response::Ok => Ok(()),
            _ => Err(StateError::InvalidStateResponse),
        }
    }

    async fn update_application(
        &mut self,
        owner: Account,
        application_id: ApplicationId,
        metadata: Metadata,
    ) -> Result<(), Self::Error> {
        let state_application_id = self.state.borrow().state_application(1).await?;
        let response = self.runtime_context.borrow_mut().call_application(
            state_application_id.with_abi::<AmsStateV1Abi>(),
            &AmsStateV1Operation::UpdateApplication {
                owner,
                application_id,
                metadata,
            },
        );
        match response {
            AmsStateV1Response::Ok => Ok(()),
            _ => Err(StateError::InvalidStateResponse),
        }
    }

    async fn application(
        &mut self,
        application_id: ApplicationId,
    ) -> Result<Option<Metadata>, Self::Error> {
        let state_application_id = self.state.borrow().state_application(1).await?;
        let response = self.runtime_context.borrow_mut().call_application(
            state_application_id.with_abi::<AmsStateV1Abi>(),
            &AmsStateV1Operation::Application { application_id },
        );
        match response {
            AmsStateV1Response::Application(application) => Ok(application),
            _ => Err(StateError::InvalidStateResponse),
        }
    }
}
