use crate::interfaces::state::StateInterface;
use abi::ams::{AmsMessage, AmsOperation};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::ApplicationId;
use runtime::interfaces::{access_control::AccessControl, contract::ContractRuntimeContext};
use std::{cell::RefCell, rc::Rc};

pub struct ClaimHandler<R: ContractRuntimeContext + AccessControl, S: StateInterface> {
    runtime: Rc<RefCell<R>>,
    _state: S,

    application_id: ApplicationId,
}

impl<R: ContractRuntimeContext + AccessControl, S: StateInterface> ClaimHandler<R, S> {
    pub fn new(runtime: Rc<RefCell<R>>, state: S, op: &AmsOperation) -> Self {
        let AmsOperation::Claim { application_id } = op else {
            panic!("Invalid operation");
        };

        Self {
            _state: state,
            runtime,

            application_id: *application_id,
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl, S: StateInterface> Handler<AmsMessage>
    for ClaimHandler<R, S>
{
    async fn handle(&mut self) -> Result<Option<HandlerOutcome<AmsMessage>>, HandlerError> {
        let destination = self.runtime.borrow_mut().application_creator_chain_id();
        let mut outcome = HandlerOutcome::new();

        outcome.with_message(
            destination,
            AmsMessage::Claim {
                application_id: self.application_id,
            },
        );

        Ok(Some(outcome))
    }
}
