pub mod errors;
pub mod interfaces;
pub mod operation;
pub mod types;

use abi::{AmsMessage, AmsOperation};
use crate::interfaces::{
    access_control::AccessControl, runtime::contract::ContractRuntimeContext, state::StateInterface,
};
use errors::HandlerError;
use interfaces::Handler;
use operation::update_value::UpdateValueHandler;

pub struct HandlerFactory;

impl HandlerFactory {
    fn new_operation_handler(
        runtime: impl ContractRuntimeContext + AccessControl + 'static,
        state: impl StateInterface + 'static,
        op: &AmsOperation,
    ) -> Box<dyn Handler> {
        match op {
            AmsOperation::UpdateValue { owner, value } => {
                Box::new(UpdateValueHandler::new(runtime, state, owner, value))
            }
            AmsOperation::ProposeOperator { operator } => {
                unimplemented!()
            }
            AmsOperation::ApproveOperator => {
                unimplemented!()
            }
            AmsOperation::RejectOperator => {
                unimplemented!()
            }
            AmsOperation::ConfirmOperator => {
                unimplemented!()
            }
            AmsOperation::UpdateCaller { caller } => {
                unimplemented!()
            }
        }
    }

    fn new_message_handler(
        _runtime: impl ContractRuntimeContext + AccessControl,
        _state: impl StateInterface,
        msg: &AmsMessage,
    ) -> Box<dyn Handler> {
        match msg {
            AmsMessage::ProposeOperator { operator } => {
                unimplemented!()
            }
            AmsMessage::ApproveOperator => {
                unimplemented!()
            }
            AmsMessage::RejectOperator => {
                unimplemented!()
            }
            AmsMessage::ConfirmOperator => {
                unimplemented!()
            }
            AmsMessage::UpdateCaller { caller } => {
                unimplemented!()
            }
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
