pub mod message;
pub mod operation;

use crate::interfaces::state::StateInterface;
use abi::{
    application_state_base::PublicStateBaseInterface,
    blob_gateway::{BlobGatewayMessage, BlobGatewayOperation, BlobGatewayResponse},
};
use base::handler::{Handler, HandlerError};
use message::register::RegisterHandler as MessageRegisterHandler;
use operation::{
    append_state::AppendStateHandler as OperationAppendStateHandler,
    handoff::HandoffHandler as OperationHandoffHandler,
    register::RegisterHandler as OperationRegisterHandler,
};
use runtime::interfaces::{access_control::AccessControl, contract::ContractRuntimeContext};
use std::{cell::RefCell, rc::Rc};

pub struct HandlerFactory;

impl HandlerFactory {
    fn new_operation_handler(
        runtime: Rc<RefCell<impl ContractRuntimeContext + AccessControl + 'static>>,
        state: impl StateInterface + PublicStateBaseInterface + 'static,
        op: &BlobGatewayOperation,
    ) -> Box<dyn Handler<BlobGatewayMessage, BlobGatewayResponse>> {
        match &op {
            BlobGatewayOperation::Register { .. } => {
                Box::new(OperationRegisterHandler::new(runtime, state, op))
            }
            BlobGatewayOperation::AppendState { .. } => {
                Box::new(OperationAppendStateHandler::new(runtime, state, op))
            }
            BlobGatewayOperation::Handoff { .. } => {
                Box::new(OperationHandoffHandler::new(runtime, state, op))
            }
        }
    }

    fn new_message_handler(
        runtime: Rc<RefCell<impl ContractRuntimeContext + AccessControl + 'static>>,
        state: impl StateInterface + 'static,
        msg: &BlobGatewayMessage,
    ) -> Box<dyn Handler<BlobGatewayMessage, BlobGatewayResponse>> {
        match &msg {
            BlobGatewayMessage::Register { .. } => {
                Box::new(MessageRegisterHandler::new(runtime, state, msg))
            }
        }
    }

    pub fn new(
        runtime: Rc<RefCell<impl ContractRuntimeContext + AccessControl + 'static>>,
        state: impl StateInterface + PublicStateBaseInterface + 'static,
        op: Option<&BlobGatewayOperation>,
        msg: Option<&BlobGatewayMessage>,
    ) -> Result<Box<dyn Handler<BlobGatewayMessage, BlobGatewayResponse>>, HandlerError> {
        if let Some(op) = op {
            return Ok(HandlerFactory::new_operation_handler(runtime, state, op));
        }
        if let Some(msg) = msg {
            return Ok(HandlerFactory::new_message_handler(runtime, state, msg));
        }
        Err(HandlerError::InvalidOperationAndMessage)
    }
}
