pub mod message;
pub mod operation;

use crate::interfaces::state::StateInterface;
use abi::state::{StateMessage, StateOperation, StateResponse};
use base::handler::{Handler, HandlerError};
use message::freeze_namespace::FreezeNamespaceMessageHandler;
use operation::{
    batch_delete::BatchDeleteHandler, batch_read::BatchReadHandler, batch_write::BatchWriteHandler,
    create_namespace::CreateNamespaceHandler, delete::DeleteHandler,
    freeze_namespace::FreezeNamespaceHandler, handoff::HandoffHandler,
    initialize_operator::InitializeOperatorHandler, read::ReadHandler,
    set_operator::SetOperatorHandler, unfreeze_namespace::UnfreezeNamespaceHandler,
    write::WriteHandler,
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
            StateOperation::BatchRead { .. } => {
                Ok(Box::new(BatchReadHandler::new(runtime, state, operation)))
            }
            StateOperation::BatchWrite { .. } => {
                Ok(Box::new(BatchWriteHandler::new(runtime, state, operation)))
            }
            StateOperation::BatchDelete { .. } => {
                Ok(Box::new(BatchDeleteHandler::new(runtime, state, operation)))
            }
            StateOperation::FreezeNamespace { .. } => {
                Ok(Box::new(FreezeNamespaceHandler::new(runtime, operation)))
            }
            StateOperation::UnfreezeNamespace { .. } => {
                Ok(Box::new(UnfreezeNamespaceHandler::new(runtime, operation)))
            }
            StateOperation::Handoff { .. } => Ok(Box::new(HandoffHandler::new(runtime, operation))),
            StateOperation::SetOperator { .. } => {
                Ok(Box::new(SetOperatorHandler::new(runtime, operation)))
            }
        }
    }

    fn new_message_handler(
        runtime: Rc<RefCell<impl ContractRuntimeContext + AccessControl + 'static>>,
        state: impl StateInterface + 'static,
        message: &StateMessage,
    ) -> Result<Box<dyn Handler<StateMessage, StateResponse>>, HandlerError> {
        match message {
            StateMessage::FreezeNamespace => {
                Ok(Box::new(FreezeNamespaceMessageHandler::new(runtime, state)))
            }
            _ => Err(HandlerError::NotImplemented),
        }
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
