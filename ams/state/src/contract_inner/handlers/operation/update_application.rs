use abi::ams::{
    abi::Metadata,
    state_v1::{AmsStateOperation, AmsStateResponse},
};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::{Account, ApplicationId};
use runtime::interfaces::{access_control::AccessControl, contract::ContractRuntimeContext};
use std::{cell::RefCell, rc::Rc};

use crate::interfaces::state::StateInterface;

pub struct UpdateApplicationHandler<R: ContractRuntimeContext + AccessControl, S: StateInterface> {
    runtime: Rc<RefCell<R>>,
    state: S,
    owner: Account,
    application_id: ApplicationId,
    metadata: Metadata,
}

impl<R: ContractRuntimeContext + AccessControl, S: StateInterface> UpdateApplicationHandler<R, S> {
    pub fn new(runtime: Rc<RefCell<R>>, state: S, operation: &AmsStateOperation) -> Self {
        let AmsStateOperation::UpdateApplication {
            owner,
            application_id,
            metadata,
        } = operation
        else {
            panic!("Invalid operation");
        };
        Self {
            runtime,
            state,
            owner: *owner,
            application_id: *application_id,
            metadata: metadata.clone(),
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl, S: StateInterface> Handler<(), AmsStateResponse>
    for UpdateApplicationHandler<R, S>
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<(), AmsStateResponse>>, HandlerError> {
        self.runtime
            .borrow_mut()
            .only_caller_creator()
            .map_err(|error| HandlerError::RuntimeError(error.into()))?;

        let caller = self
            .runtime
            .borrow_mut()
            .require_authenticated_caller_id()
            .map_err(|error| HandlerError::RuntimeError(error.into()))?;

        let business_application_id = self
            .state
            .business_application_id()
            .await
            .map_err(|error| HandlerError::ProcessError(error.into()))?;

        if caller != business_application_id {
            return Err(HandlerError::NotAllowed);
        }

        let application = self
            .state
            .application(self.application_id)
            .await
            .map_err(|error| HandlerError::ProcessError(error.into()))?
            .ok_or(HandlerError::NotAllowed)?;

        if application.creator != self.owner {
            return Err(HandlerError::NotAllowed);
        }

        let application_types = self
            .state
            .application_types()
            .await
            .map_err(|error| HandlerError::ProcessError(error.into()))?;

        if !application_types.contains(&self.metadata.application_type) {
            return Err(HandlerError::NotAllowed);
        }

        self.state
            .update_application(self.application_id, self.metadata.clone())
            .await
            .map_err(|error| HandlerError::ProcessError(error.into()))?;

        let mut outcome = HandlerOutcome::new();
        outcome.with_response(AmsStateResponse::Ok);
        Ok(Some(outcome))
    }
}
