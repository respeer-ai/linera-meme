pub mod message;
pub mod operation;

use crate::interfaces::state::StateInterface;
use abi::state::{StateMessage, StateOperation, StateResponse};
use base::handler::{Handler, HandlerError};
use operation::{
    create_namespace::CreateNamespaceHandler, delete::DeleteHandler,
    initialize_operator::InitializeOperatorHandler, read::ReadHandler, write::WriteHandler,
};
use runtime::interfaces::{access_control::AccessControl, contract::ContractRuntimeContext};
use std::{cell::RefCell, rc::Rc};

pub struct HandlerFactory;

impl HandlerFactory {
    fn new_operation_handler(
        runtime: Rc<RefCell<impl ContractRuntimeContext + AccessControl + 'static>>,
        state: impl StateInterface + 'static,
        operation: &StateOperation,
    ) -> Result<Box<dyn Handler<StateMessage, StateResponse>>, HandlerError> {
        match operation {
            StateOperation::InitializeOperator { .. } => Ok(Box::new(
                InitializeOperatorHandler::new(runtime, state, operation),
            )),
            StateOperation::CreateNamespace { .. } => Ok(Box::new(CreateNamespaceHandler::new(
                runtime, state, operation,
            ))),
            StateOperation::Read { .. } => {
                Ok(Box::new(ReadHandler::new(runtime, state, operation)))
            }
            StateOperation::Write { .. } => {
                Ok(Box::new(WriteHandler::new(runtime, state, operation)))
            }
            StateOperation::Delete { .. } => {
                Ok(Box::new(DeleteHandler::new(runtime, state, operation)))
            }
            _ => Err(HandlerError::NotImplemented),
        }
    }

    fn new_message_handler(
        _runtime: Rc<RefCell<impl ContractRuntimeContext + AccessControl + 'static>>,
        _state: impl StateInterface + 'static,
        _message: &StateMessage,
    ) -> Result<Box<dyn Handler<StateMessage, StateResponse>>, HandlerError> {
        Err(HandlerError::NotImplemented)
    }

    pub fn new(
        runtime: Rc<RefCell<impl ContractRuntimeContext + AccessControl + 'static>>,
        state: impl StateInterface + 'static,
        operation: Option<&StateOperation>,
        message: Option<&StateMessage>,
    ) -> Result<Box<dyn Handler<StateMessage, StateResponse>>, HandlerError> {
        if let Some(operation) = operation {
            return HandlerFactory::new_operation_handler(runtime, state, operation);
        }
        if let Some(message) = message {
            return HandlerFactory::new_message_handler(runtime, state, message);
        }
        Err(HandlerError::InvalidOperationAndMessage)
    }
}
