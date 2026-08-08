pub mod operation;

use abi::blob_gateway::state_v1::{BlobGatewayStateV1Operation, BlobGatewayStateV1Response};
use base::handler::{Handler, HandlerError};
use runtime::interfaces::{access_control::AccessControl, contract::ContractRuntimeContext};
use std::{cell::RefCell, rc::Rc};

use crate::interfaces::state::StateInterface;
use operation::blob::BlobHandler;
use operation::blobs::BlobsHandler;
use operation::create_blob::CreateBlobHandler;
use operation::handoff::HandoffHandler;
use operation::set_operator::SetOperatorHandler;

pub struct HandlerFactory;

impl HandlerFactory {
    fn new_operation_handler(
        runtime: Rc<RefCell<impl ContractRuntimeContext<Message = ()> + AccessControl + 'static>>,
        state: impl StateInterface + 'static,
        operation: &BlobGatewayStateV1Operation,
    ) -> Result<Box<dyn Handler<(), BlobGatewayStateV1Response>>, HandlerError> {
        match operation {
            BlobGatewayStateV1Operation::SetOperator { .. } => {
                Ok(Box::new(SetOperatorHandler::new(runtime, state, operation)))
            }
            BlobGatewayStateV1Operation::CreateBlob { .. } => {
                Ok(Box::new(CreateBlobHandler::new(runtime, state, operation)))
            }
            BlobGatewayStateV1Operation::Blob { .. } => {
                Ok(Box::new(BlobHandler::new(state, operation)))
            }
            BlobGatewayStateV1Operation::Blobs => Ok(Box::new(BlobsHandler::new(state))),
            BlobGatewayStateV1Operation::Handoff { .. } => {
                Ok(Box::new(HandoffHandler::new(runtime, state, operation)))
            }
        }
    }

    pub fn new(
        runtime: Rc<RefCell<impl ContractRuntimeContext<Message = ()> + AccessControl + 'static>>,
        state: impl StateInterface + 'static,
        operation: Option<&BlobGatewayStateV1Operation>,
        message: Option<&()>,
    ) -> Result<Box<dyn Handler<(), BlobGatewayStateV1Response>>, HandlerError> {
        if let Some(operation) = operation {
            return Self::new_operation_handler(runtime, state, operation);
        }
        if message.is_some() {
            return Err(HandlerError::NotImplemented);
        }
        Err(HandlerError::InvalidOperationAndMessage)
    }
}
