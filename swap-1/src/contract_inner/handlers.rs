pub mod create_pool;
pub mod message;
pub mod operation;

use crate::interfaces::state::StateInterface;
use abi::swap::router::{SwapMessage, SwapOperation};
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
        op: &SwapOperation,
    ) -> Box<dyn Handler<SwapMessage>> {
        match op {
            SwapOperation::Register { metadata } => {
                Box::new(OperationRegisterHandler::new(runtime, state, metadata))
            }
            SwapOperation::Claim { application_id } => {
                Box::new(OperationClaimHandler::new(runtime, state, *application_id))
            }
            SwapOperation::AddApplicationType { application_type } => Box::new(
                OperationAddApplicationTypeHandler::new(runtime, state, application_type.clone()),
            ),
            SwapOperation::Update {
                application_id,
                metadata,
            } => Box::new(OperationUpdateHandler::new(
                runtime,
                state,
                *application_id,
                metadata,
            )),
        }
    }

    fn new_message_handler(
        runtime: Rc<RefCell<impl ContractRuntimeContext + AccessControl + 'static>>,
        state: impl StateInterface + 'static,
        msg: &SwapMessage,
    ) -> Box<dyn Handler<SwapMessage>> {
        match msg {
            SwapMessage::Register { metadata } => {
                Box::new(MessageRegisterHandler::new(runtime, state, metadata))
            }
            SwapMessage::Claim { application_id } => {
                Box::new(MessageClaimHandler::new(runtime, state, *application_id))
            }
            SwapMessage::AddApplicationType {
                owner,
                application_type,
            } => Box::new(MessageAddApplicationTypeHandler::new(
                runtime,
                state,
                *owner,
                application_type.clone(),
            )),
            SwapMessage::Update {
                owner,
                application_id,
                metadata,
            } => Box::new(MessageUpdateHandler::new(
                runtime,
                state,
                *owner,
                *application_id,
                metadata,
            )),
        }
    }

    pub fn new(
        runtime: Rc<RefCell<impl ContractRuntimeContext + AccessControl + 'static>>,
        state: impl StateInterface + 'static,
        op: Option<&SwapOperation>,
        msg: Option<&SwapMessage>,
    ) -> Result<Box<dyn Handler<SwapMessage>>, HandlerError> {
        if let Some(op) = op {
            return Ok(HandlerFactory::new_operation_handler(runtime, state, op));
        }
        if let Some(msg) = msg {
            return Ok(HandlerFactory::new_message_handler(runtime, state, msg));
        }
        Err(HandlerError::InvalidOperationAndMessage)
    }
}
