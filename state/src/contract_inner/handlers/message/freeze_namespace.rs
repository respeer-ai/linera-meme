use crate::interfaces::state::StateInterface;
use abi::state::{StateMessage, StateResponse};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use runtime::interfaces::contract::ContractRuntimeContext;
use std::{cell::RefCell, rc::Rc};

pub struct FreezeNamespaceMessageHandler<R: ContractRuntimeContext, S: StateInterface> {
    runtime: Rc<RefCell<R>>,
    state: S,
}

impl<R: ContractRuntimeContext, S: StateInterface> FreezeNamespaceMessageHandler<R, S> {
    pub fn new(runtime: Rc<RefCell<R>>, state: S) -> Self {
        Self { runtime, state }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext, S: StateInterface> Handler<StateMessage, StateResponse>
    for FreezeNamespaceMessageHandler<R, S>
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<StateMessage, StateResponse>>, HandlerError> {
        let message_operator = self.runtime.borrow_mut().message_signer_account();
        let operator = self
            .state
            .operator()
            .await
            .map_err(|error| HandlerError::ProcessError(error.into()))?;

        if message_operator != operator {
            return Err(HandlerError::NotAllowed);
        }

        self.state
            .freeze_namespace()
            .await
            .map_err(|error| HandlerError::ProcessError(error.into()))?;

        Ok(Some(HandlerOutcome::new()))
    }
}
