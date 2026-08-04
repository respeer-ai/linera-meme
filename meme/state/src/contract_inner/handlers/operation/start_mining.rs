use abi::meme::{MemeStateV1Operation, MemeStateV1Response};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use runtime::interfaces::{access_control::AccessControl, contract::ContractRuntimeContext};
use std::{cell::RefCell, rc::Rc};

use crate::interfaces::state::StateInterface;

pub struct StartMiningHandler<R: ContractRuntimeContext + AccessControl, S: StateInterface> {
    runtime: Rc<RefCell<R>>,
    state: S,
}

impl<R: ContractRuntimeContext + AccessControl, S: StateInterface> StartMiningHandler<R, S> {
    pub fn new(runtime: Rc<RefCell<R>>, state: S, _operation: &MemeStateV1Operation) -> Self {
        Self { runtime, state }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl, S: StateInterface> Handler<(), MemeStateV1Response>
    for StartMiningHandler<R, S>
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<(), MemeStateV1Response>>, HandlerError> {
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

        self.state
            .start_mining()
            .await
            .map_err(|error| HandlerError::ProcessError(error.into()))?;

        let mut outcome = HandlerOutcome::new();
        outcome.with_response(MemeStateV1Response::Ok);
        Ok(Some(outcome))
    }
}
