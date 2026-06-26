use abi::state::{StateMessage, StateOperation, StateResponse};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::{Account, ApplicationId};
use runtime::interfaces::contract::ContractRuntimeContext;
use std::{cell::RefCell, rc::Rc};

pub struct SetOperatorHandler<R: ContractRuntimeContext> {
    runtime: Rc<RefCell<R>>,
    application_id: ApplicationId,
    new_operator: Account,
}

impl<R: ContractRuntimeContext> SetOperatorHandler<R> {
    pub fn new(runtime: Rc<RefCell<R>>, operation: &StateOperation) -> Self {
        let StateOperation::SetOperator {
            application_id,
            new_operator,
        } = operation
        else {
            panic!("Invalid operation");
        };

        Self {
            runtime,
            application_id: *application_id,
            new_operator: *new_operator,
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext> Handler<StateMessage, StateResponse> for SetOperatorHandler<R> {
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
        outcome.with_message(
            target_chain_id,
            StateMessage::SetOperator {
                new_operator: self.new_operator,
            },
            false,
        );
        outcome.with_response(StateResponse::Ok);
        Ok(Some(outcome))
    }
}
