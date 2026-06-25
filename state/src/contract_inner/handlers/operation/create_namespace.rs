use crate::interfaces::state::StateInterface;
use abi::state::{StateMessage, StateOperation, StateResponse};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use runtime::interfaces::{access_control::AccessControl, contract::ContractRuntimeContext};
use std::{cell::RefCell, rc::Rc};

pub struct CreateNamespaceHandler<R: ContractRuntimeContext + AccessControl, S: StateInterface> {
    runtime: Rc<RefCell<R>>,
    state: S,
    namespace: u8,
}

impl<R: ContractRuntimeContext + AccessControl, S: StateInterface> CreateNamespaceHandler<R, S> {
    pub fn new(runtime: Rc<RefCell<R>>, state: S, operation: &StateOperation) -> Self {
        let StateOperation::CreateNamespace { namespace } = operation else {
            panic!("Invalid operation");
        };

        Self {
            runtime,
            state,
            namespace: *namespace,
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl, S: StateInterface>
    Handler<StateMessage, StateResponse> for CreateNamespaceHandler<R, S>
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<StateMessage, StateResponse>>, HandlerError> {
        self.runtime
            .borrow_mut()
            .only_caller_creator()
            .map_err(|error| HandlerError::RuntimeError(error.into()))?;

        let caller = self
            .runtime
            .borrow_mut()
            .require_authenticated_caller_id()
            .map_err(|error| HandlerError::RuntimeError(error.into()))?;

        self.state
            .create_namespace(self.namespace, caller)
            .await
            .map_err(|error| HandlerError::ProcessError(error.into()))?;

        let mut outcome = HandlerOutcome::new();
        outcome.with_response(StateResponse::Ok);
        Ok(Some(outcome))
    }
}
