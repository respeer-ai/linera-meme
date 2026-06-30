pub mod operation;

use abi::ams::state_v1::{AmsStateOperation, AmsStateResponse};
use base::handler::{Handler, HandlerError};
use runtime::interfaces::{access_control::AccessControl, contract::ContractRuntimeContext};
use std::{cell::RefCell, rc::Rc};

use crate::interfaces::state::StateInterface;
use operation::add_application_type::AddApplicationTypeHandler;
use operation::application::ApplicationHandler;
use operation::claim_application::ClaimApplicationHandler;
use operation::handoff::HandoffHandler;
use operation::register_application::RegisterApplicationHandler;
use operation::set_operator::SetOperatorHandler;
use operation::update_application::UpdateApplicationHandler;

pub struct HandlerFactory;

impl HandlerFactory {
    fn new_operation_handler(
        runtime: Rc<RefCell<impl ContractRuntimeContext<Message = ()> + AccessControl + 'static>>,
        state: impl StateInterface + 'static,
        operation: &AmsStateOperation,
    ) -> Result<Box<dyn Handler<(), AmsStateResponse>>, HandlerError> {
        match operation {
            AmsStateOperation::Application { .. } => {
                Ok(Box::new(ApplicationHandler::new(state, operation)))
            }
            AmsStateOperation::SetOperator { .. } => {
                Ok(Box::new(SetOperatorHandler::new(runtime, state, operation)))
            }
            AmsStateOperation::AddApplicationType { .. } => Ok(Box::new(
                AddApplicationTypeHandler::new(runtime, state, operation),
            )),
            AmsStateOperation::RegisterApplication { .. } => Ok(Box::new(
                RegisterApplicationHandler::new(runtime, state, operation),
            )),
            AmsStateOperation::ClaimApplication { .. } => Ok(Box::new(
                ClaimApplicationHandler::new(runtime, state, operation),
            )),
            AmsStateOperation::UpdateApplication { .. } => Ok(Box::new(
                UpdateApplicationHandler::new(runtime, state, operation),
            )),
            AmsStateOperation::Handoff { .. } => {
                Ok(Box::new(HandoffHandler::new(runtime, state, operation)))
            }
        }
    }

    pub fn new(
        runtime: Rc<RefCell<impl ContractRuntimeContext<Message = ()> + AccessControl + 'static>>,
        state: impl StateInterface + 'static,
        operation: Option<&AmsStateOperation>,
        message: Option<&()>,
    ) -> Result<Box<dyn Handler<(), AmsStateResponse>>, HandlerError> {
        if let Some(operation) = operation {
            return Self::new_operation_handler(runtime, state, operation);
        }
        if message.is_some() {
            return Err(HandlerError::NotImplemented);
        }
        Err(HandlerError::InvalidOperationAndMessage)
    }
}
