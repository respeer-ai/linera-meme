use crate::interfaces::state::StateInterface;
use abi::state::{StateMessage, StateOperation, StateResponse};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::Account;
use runtime::interfaces::{access_control::AccessControl, contract::ContractRuntimeContext};
use std::{cell::RefCell, rc::Rc};

pub struct InitializeOperatorHandler<R: ContractRuntimeContext + AccessControl, S: StateInterface> {
    runtime: Rc<RefCell<R>>,
    state: S,
    operator: Account,
}

impl<R: ContractRuntimeContext + AccessControl, S: StateInterface> InitializeOperatorHandler<R, S> {
    pub fn new(runtime: Rc<RefCell<R>>, state: S, operation: &StateOperation) -> Self {
        let StateOperation::InitializeOperator { operator } = operation else {
            panic!("Invalid operation");
        };

        Self {
            runtime,
            state,
            operator: *operator,
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl, S: StateInterface>
    Handler<StateMessage, StateResponse> for InitializeOperatorHandler<R, S>
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<StateMessage, StateResponse>>, HandlerError> {
        self.runtime
            .borrow_mut()
            .only_caller_creator()
            .map_err(|error| HandlerError::RuntimeError(error.into()))?;

        self.state
            .initialize_operator(self.operator)
            .await
            .map_err(|error| HandlerError::ProcessError(error.into()))?;

        let mut outcome = HandlerOutcome::new();
        outcome.with_response(StateResponse::Ok);
        Ok(Some(outcome))
    }
}
