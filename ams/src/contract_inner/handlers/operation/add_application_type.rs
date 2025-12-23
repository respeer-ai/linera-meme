use crate::interfaces::state::StateInterface;
use abi::ams::{AmsMessage, AmsOperation};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use runtime::interfaces::{access_control::AccessControl, contract::ContractRuntimeContext};
use std::{cell::RefCell, rc::Rc};

pub struct AddApplicationTypeHandler<R: ContractRuntimeContext + AccessControl, S: StateInterface> {
    runtime: Rc<RefCell<R>>,
    _state: S,

    application_type: String,
}

impl<R: ContractRuntimeContext + AccessControl, S: StateInterface> AddApplicationTypeHandler<R, S> {
    pub fn new(runtime: Rc<RefCell<R>>, state: S, op: &AmsOperation) -> Self {
        let AmsOperation::AddApplicationType { application_type } = op else {
            panic!("Invalid operation");
        };

        Self {
            _state: state,
            runtime,

            application_type: application_type.clone(),
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl, S: StateInterface> Handler<AmsMessage>
    for AddApplicationTypeHandler<R, S>
{
    async fn handle(&mut self) -> Result<Option<HandlerOutcome<AmsMessage>>, HandlerError> {
        let destination = self.runtime.borrow_mut().application_creator_chain_id();
        let mut outcome = HandlerOutcome::new();

        let owner = self.runtime.borrow_mut().authenticated_account();

        outcome.with_message(
            destination,
            AmsMessage::AddApplicationType {
                owner,
                application_type: self.application_type.clone(),
            },
        );

        Ok(Some(outcome))
    }
}
