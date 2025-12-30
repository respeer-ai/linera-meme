pub mod message;
pub mod operation;

use crate::interfaces::state::StateInterface;
use abi::ams::{AmsMessage, AmsOperation, AmsResponse};
use base::handler::Handler;
use base::handler::HandlerError;
use message::{
    add_application_type::AddApplicationTypeHandler as MessageAddApplicationTypeHandler,
    claim::ClaimHandler as MessageClaimHandler,
    register::RegisterHandler as MessageRegisterHandler,
    update::UpdateHandler as MessageUpdateHandler,
};
use operation::{
    add_application_type::AddApplicationTypeHandler as OperationAddApplicationTypeHandler,
    claim::ClaimHandler as OperationClaimHandler,
    register::RegisterHandler as OperationRegisterHandler,
    update::UpdateHandler as OperationUpdateHandler,
};
use runtime::interfaces::{access_control::AccessControl, contract::ContractRuntimeContext};
use std::{cell::RefCell, rc::Rc};

pub struct HandlerFactory;

impl HandlerFactory {
    fn new_operation_handler(
        runtime: Rc<RefCell<impl ContractRuntimeContext + AccessControl + 'static>>,
        state: impl StateInterface + 'static,
        op: &AmsOperation,
    ) -> Box<dyn Handler<AmsMessage, AmsResponse>> {
        match &op {
            AmsOperation::Register { .. } => {
                Box::new(OperationRegisterHandler::new(runtime, state, op))
            }
            AmsOperation::Claim { .. } => Box::new(OperationClaimHandler::new(runtime, state, op)),
            AmsOperation::AddApplicationType { .. } => {
                Box::new(OperationAddApplicationTypeHandler::new(runtime, state, op))
            }
            AmsOperation::Update { .. } => {
                Box::new(OperationUpdateHandler::new(runtime, state, op))
            }
        }
    }

    fn new_message_handler(
        runtime: Rc<RefCell<impl ContractRuntimeContext + AccessControl + 'static>>,
        state: impl StateInterface + 'static,
        msg: &AmsMessage,
    ) -> Box<dyn Handler<AmsMessage, AmsResponse>> {
        match &msg {
            AmsMessage::Register { .. } => {
                Box::new(MessageRegisterHandler::new(runtime, state, msg))
            }
            AmsMessage::Claim { .. } => Box::new(MessageClaimHandler::new(runtime, state, msg)),
            AmsMessage::AddApplicationType { .. } => {
                Box::new(MessageAddApplicationTypeHandler::new(runtime, state, msg))
            }
            AmsMessage::Update { .. } => Box::new(MessageUpdateHandler::new(runtime, state, msg)),
        }
    }

    pub fn new(
        runtime: Rc<RefCell<impl ContractRuntimeContext + AccessControl + 'static>>,
        state: impl StateInterface + 'static,
        op: Option<&AmsOperation>,
        msg: Option<&AmsMessage>,
    ) -> Result<Box<dyn Handler<AmsMessage, AmsResponse>>, HandlerError> {
        if let Some(op) = op {
            return Ok(HandlerFactory::new_operation_handler(runtime, state, op));
        }
        if let Some(msg) = msg {
            return Ok(HandlerFactory::new_message_handler(runtime, state, msg));
        }
        Err(HandlerError::InvalidOperationAndMessage)
    }
}
