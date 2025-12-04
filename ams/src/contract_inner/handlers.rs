pub mod message;
pub mod operation;

use crate::interfaces::state::StateInterface;
use abi::ams::{AmsMessage, AmsOperation};
use base::handler::Handler;
use base::handler::HandlerError;
use message::{
    claim::ClaimHandler as MessageClaimHandler, register::RegisterHandler as MessageRegisterHandler,
};
use operation::{
    claim::ClaimHandler as OperationClaimHandler,
    register::RegisterHandler as OperationRegisterHandler,
};
use runtime::interfaces::{access_control::AccessControl, contract::ContractRuntimeContext};
use std::{cell::RefCell, rc::Rc};

pub struct HandlerFactory;

impl HandlerFactory {
    fn new_operation_handler(
        runtime: Rc<RefCell<impl ContractRuntimeContext + AccessControl + 'static>>,
        state: impl StateInterface + 'static,
        op: &AmsOperation,
    ) -> Box<dyn Handler<AmsMessage>> {
        match op {
            AmsOperation::Register { metadata } => {
                Box::new(OperationRegisterHandler::new(runtime, state, metadata))
            }
            AmsOperation::Claim { application_id } => {
                Box::new(OperationClaimHandler::new(runtime, state, *application_id))
            }
            AmsOperation::AddApplicationType { application_type } => unimplemented!(),
            AmsOperation::Update {
                application_id,
                metadata,
            } => unimplemented!(),
        }
    }

    fn new_message_handler(
        runtime: Rc<RefCell<impl ContractRuntimeContext + AccessControl + 'static>>,
        state: impl StateInterface + 'static,
        msg: &AmsMessage,
    ) -> Box<dyn Handler<AmsMessage>> {
        match msg {
            AmsMessage::Register { metadata } => {
                Box::new(MessageRegisterHandler::new(runtime, state, metadata))
            }
            AmsMessage::Claim { application_id } => {
                Box::new(MessageClaimHandler::new(runtime, state, *application_id))
            }
            AmsMessage::AddApplicationType {
                owner,
                application_type,
            } => unimplemented!(),
            AmsMessage::Update {
                owner,
                application_id,
                metadata,
            } => unimplemented!(),
        }
    }

    pub fn new(
        runtime: Rc<RefCell<impl ContractRuntimeContext + AccessControl + 'static>>,
        state: impl StateInterface + 'static,
        op: Option<&AmsOperation>,
        msg: Option<&AmsMessage>,
    ) -> Result<Box<dyn Handler<AmsMessage>>, HandlerError> {
        if let Some(op) = op {
            return Ok(HandlerFactory::new_operation_handler(runtime, state, op));
        }
        if let Some(msg) = msg {
            return Ok(HandlerFactory::new_message_handler(runtime, state, msg));
        }
        Err(HandlerError::InvalidOperationAndMessage)
    }
}
