use crate::interfaces::state::StateInterface;
use abi::state::{StateMessage, StateResponse};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::Account;
use runtime::interfaces::contract::ContractRuntimeContext;
use std::{cell::RefCell, rc::Rc};

pub struct SetOperatorMessageHandler<R: ContractRuntimeContext, S: StateInterface> {
    runtime: Rc<RefCell<R>>,
    state: S,
    new_operator: Account,
}

impl<R: ContractRuntimeContext, S: StateInterface> SetOperatorMessageHandler<R, S> {
    pub fn new(runtime: Rc<RefCell<R>>, state: S, message: &StateMessage) -> Self {
        let StateMessage::SetOperator { new_operator } = message else {
            panic!("Invalid message");
        };

        Self {
            runtime,
            state,
            new_operator: *new_operator,
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext, S: StateInterface> Handler<StateMessage, StateResponse>
    for SetOperatorMessageHandler<R, S>
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
            .set_operator(self.new_operator)
            .await
            .map_err(|error| HandlerError::ProcessError(error.into()))?;

        Ok(Some(HandlerOutcome::new()))
    }
}
