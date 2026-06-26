use crate::interfaces::state::StateInterface;
use abi::state::{StateMessage, StateResponse};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::ApplicationId;
use runtime::interfaces::contract::ContractRuntimeContext;
use std::{cell::RefCell, rc::Rc};

pub struct HandoffMessageHandler<R: ContractRuntimeContext, S: StateInterface> {
    runtime: Rc<RefCell<R>>,
    state: S,
    application_id: ApplicationId,
    namespace: u8,
    new_application_id: ApplicationId,
}

impl<R: ContractRuntimeContext, S: StateInterface> HandoffMessageHandler<R, S> {
    pub fn new(runtime: Rc<RefCell<R>>, state: S, message: &StateMessage) -> Self {
        let StateMessage::Handoff {
            application_id,
            namespace,
            new_application_id,
        } = message
        else {
            panic!("Invalid message");
        };

        Self {
            runtime,
            state,
            application_id: *application_id,
            namespace: *namespace,
            new_application_id: *new_application_id,
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext, S: StateInterface> Handler<StateMessage, StateResponse>
    for HandoffMessageHandler<R, S>
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

        let target_chain_id = self
            .runtime
            .borrow_mut()
            .creator_chain_id(self.application_id);
        let new_target_chain_id = self
            .runtime
            .borrow_mut()
            .creator_chain_id(self.new_application_id);

        if target_chain_id != new_target_chain_id {
            return Err(HandlerError::NotAllowed);
        }

        self.state
            .handoff(self.namespace, self.application_id, self.new_application_id)
            .await
            .map_err(|error| HandlerError::ProcessError(error.into()))?;

        Ok(Some(HandlerOutcome::new()))
    }
}
