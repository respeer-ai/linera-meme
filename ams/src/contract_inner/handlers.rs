pub mod errors;
pub mod interfaces;
pub mod operation;
pub mod types;

use crate::interfaces::state::StateInterface;
use abi::ams::{AmsMessage, AmsOperation};
use errors::HandlerError;
use interfaces::Handler;
use operation::register::RegisterHandler;
use runtime::interfaces::{access_control::AccessControl, contract::ContractRuntimeContext};

pub struct HandlerFactory;

impl HandlerFactory {
    fn new_operation_handler(
        runtime: impl ContractRuntimeContext + AccessControl + 'static,
        state: impl StateInterface + 'static,
        op: &AmsOperation,
    ) -> Box<dyn Handler> {
        match op {
            AmsOperation::Register { metadata } => {
                Box::new(RegisterHandler::new(runtime, state, metadata))
            }
            AmsOperation::Claim { application_id } => unimplemented!(),
            AmsOperation::AddApplicationType { application_type } => unimplemented!(),
            AmsOperation::Update {
                application_id,
                metadata,
            } => unimplemented!(),
        }
    }

    fn new_message_handler(
        _runtime: impl ContractRuntimeContext + AccessControl,
        _state: impl StateInterface,
        msg: &AmsMessage,
    ) -> Box<dyn Handler> {
        match msg {
            AmsMessage::Register { metadata } => unimplemented!(),
            AmsMessage::Claim { application_id } => unimplemented!(),
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
        runtime: impl ContractRuntimeContext + AccessControl + 'static,
        state: impl StateInterface + 'static,
        op: Option<&AmsOperation>,
        msg: Option<&AmsMessage>,
    ) -> Result<Box<dyn Handler>, HandlerError> {
        if let Some(op) = op {
            return Ok(HandlerFactory::new_operation_handler(runtime, state, op));
        }
        if let Some(msg) = msg {
            return Ok(HandlerFactory::new_message_handler(runtime, state, msg));
        }
        Err(HandlerError::InvalidOperationAndMessage)
    }
}
