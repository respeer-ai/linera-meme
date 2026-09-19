use crate::interfaces::state::StateInterface;
use abi::pool::state_v1::{PoolStateV1Operation, PoolStateV1Response};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use runtime::interfaces::{access_control::AccessControl, contract::ContractRuntimeContext};
use std::{cell::RefCell, rc::Rc};

pub struct PoolHandler<R: ContractRuntimeContext + AccessControl, S: StateInterface> {
    runtime: Rc<RefCell<R>>,
    state: S,
}

impl<R: ContractRuntimeContext + AccessControl, S: StateInterface> PoolHandler<R, S> {
    pub fn new(runtime: Rc<RefCell<R>>, state: S, op: &PoolStateV1Operation) -> Self {
        let PoolStateV1Operation::Pool = op else {
            panic!("Invalid operation");
        };
        Self { runtime, state }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl, S: StateInterface> Handler<(), PoolStateV1Response>
    for PoolHandler<R, S>
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<(), PoolStateV1Response>>, HandlerError> {
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

        let pool = self
            .state
            .pool()
            .await
            .map_err(|error| HandlerError::ProcessError(Box::new(error)))?;

        let mut outcome = HandlerOutcome::new();
        outcome.with_response(PoolStateV1Response::Pool(pool));
        Ok(Some(outcome))
    }
}
