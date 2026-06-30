use abi::ams::state_v1::{AmsStateOperation, AmsStateResponse};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::Account;
use runtime::interfaces::{access_control::AccessControl, contract::ContractRuntimeContext};
use std::{cell::RefCell, rc::Rc};

use crate::interfaces::state::StateInterface;

pub struct AddApplicationTypeHandler<R: ContractRuntimeContext + AccessControl, S: StateInterface> {
    runtime: Rc<RefCell<R>>,
    state: S,
    owner: Account,
    application_type: String,
}

impl<R: ContractRuntimeContext + AccessControl, S: StateInterface> AddApplicationTypeHandler<R, S> {
    pub fn new(runtime: Rc<RefCell<R>>, state: S, operation: &AmsStateOperation) -> Self {
        let AmsStateOperation::AddApplicationType {
            owner,
            application_type,
        } = operation
        else {
            panic!("Invalid operation");
        };
        Self {
            runtime,
            state,
            owner: *owner,
            application_type: application_type.clone(),
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl, S: StateInterface> Handler<(), AmsStateResponse>
    for AddApplicationTypeHandler<R, S>
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

        let operator = self
            .state
            .operator()
            .await
            .map_err(|error| HandlerError::ProcessError(error.into()))?;

        if self.owner != operator {
            return Err(HandlerError::NotAllowed);
        }

        self.state
            .add_application_type(self.application_type.clone())
            .await
            .map_err(|error| HandlerError::ProcessError(error.into()))?;

        let mut outcome = HandlerOutcome::new();
        outcome.with_response(AmsStateResponse::Ok);
        Ok(Some(outcome))
    }
}
