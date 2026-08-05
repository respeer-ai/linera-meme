use abi::meme::{MemeStateV1Operation, MemeStateV1Response};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use runtime::interfaces::{access_control::AccessControl, contract::ContractRuntimeContext};
use std::{cell::RefCell, rc::Rc};

use crate::interfaces::state::StateInterface;

pub struct OwnerHandler<S: StateInterface> {
    state: S,
}

impl<S: StateInterface> OwnerHandler<S> {
    pub fn new<R: ContractRuntimeContext + AccessControl>(
        _runtime: Rc<RefCell<R>>,
        state: S,
        _operation: &MemeStateV1Operation,
    ) -> Self {
        Self { state }
    }
}

#[async_trait(?Send)]
impl<S: StateInterface> Handler<(), MemeStateV1Response> for OwnerHandler<S> {
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<(), MemeStateV1Response>>, HandlerError> {
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
