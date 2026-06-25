use abi::state::{StateMessage, StateOperation, StateResponse};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::ApplicationId;
use runtime::interfaces::contract::ContractRuntimeContext;
use std::{cell::RefCell, rc::Rc};

pub struct FreezeNamespaceHandler<R: ContractRuntimeContext> {
    runtime: Rc<RefCell<R>>,
    application_id: ApplicationId,
}

impl<R: ContractRuntimeContext> FreezeNamespaceHandler<R> {
    pub fn new(runtime: Rc<RefCell<R>>, operation: &StateOperation) -> Self {
        let StateOperation::FreezeNamespace { application_id } = operation else {
            panic!("Invalid operation");
        };

        Self {
            runtime,
            application_id: *application_id,
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext> Handler<StateMessage, StateResponse> for FreezeNamespaceHandler<R> {
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<StateMessage, StateResponse>>, HandlerError> {
        self.runtime
            .borrow_mut()
            .require_authenticated_signer()
            .map_err(|error| HandlerError::RuntimeError(error.into()))?;

        let target_chain_id = self
            .runtime
            .borrow_mut()
            .creator_chain_id(self.application_id);

        let mut outcome = HandlerOutcome::new();
        outcome.with_message(target_chain_id, StateMessage::FreezeNamespace, false);
        outcome.with_response(StateResponse::Ok);
        Ok(Some(outcome))
    }
}
