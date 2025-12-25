use crate::interfaces::state::StateInterface;
use abi::ams::{AmsMessage, AmsOperation, Metadata};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use runtime::interfaces::{access_control::AccessControl, contract::ContractRuntimeContext};
use std::{cell::RefCell, rc::Rc};

pub struct RegisterHandler<R: ContractRuntimeContext + AccessControl, S: StateInterface> {
    runtime: Rc<RefCell<R>>,
    _state: S,

    metadata: Metadata,
}

impl<R: ContractRuntimeContext + AccessControl, S: StateInterface> RegisterHandler<R, S> {
    pub fn new(runtime: Rc<RefCell<R>>, state: S, op: &AmsOperation) -> Self {
        let AmsOperation::Register { metadata } = op else {
            panic!("Invalid operation");
        };

        Self {
            _state: state,
            runtime,

            metadata: metadata.clone(),
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl, S: StateInterface> Handler<AmsMessage>
    for RegisterHandler<R, S>
{
    async fn handle(&mut self) -> Result<Option<HandlerOutcome<AmsMessage>>, HandlerError> {
        self.metadata.creator = self.runtime.borrow_mut().authenticated_account();
        self.metadata.created_at = self.runtime.borrow_mut().system_time();

        let destination = self.runtime.borrow_mut().application_creator_chain_id();
        let mut outcome = HandlerOutcome::new();

        outcome.with_message(
            destination,
            AmsMessage::Register {
                metadata: self.metadata.clone(),
            },
        );

        Ok(Some(outcome))
    }
}
