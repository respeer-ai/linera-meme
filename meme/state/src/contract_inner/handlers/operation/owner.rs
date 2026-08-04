use abi::meme::{MemeStateV1Operation, MemeStateV1Response};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use runtime::interfaces::{access_control::AccessControl, contract::ContractRuntimeContext};
use std::{cell::RefCell, rc::Rc};

use crate::interfaces::state::StateInterface;

pub struct OwnerHandler<R: ContractRuntimeContext + AccessControl, S: StateInterface> {
    runtime: Rc<RefCell<R>>,
    state: S,
}

impl<R: ContractRuntimeContext + AccessControl, S: StateInterface> OwnerHandler<R, S> {
    pub fn new(runtime: Rc<RefCell<R>>, state: S, _operation: &MemeStateV1Operation) -> Self {
        Self { runtime, state }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl, S: StateInterface> Handler<(), MemeStateV1Response>
    for OwnerHandler<R, S>
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<(), MemeStateV1Response>>, HandlerError> {
        self.runtime
            .borrow_mut()
            .only_caller_creator()
            .map_err(|error| HandlerError::RuntimeError(error.into()))?;

        let owner = self
            .state
            .owner()
            .await
            .map_err(|error| HandlerError::ProcessError(error.into()))?;

        let mut outcome = HandlerOutcome::new();
        outcome.with_response(MemeStateV1Response::Owner(owner));
        Ok(Some(outcome))
    }
}
