use crate::interfaces::state::StateInterface;
use abi::ams::{AmsMessage, AmsOperation, AmsResponse, Metadata};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::{Account, ApplicationId};
use runtime::interfaces::{access_control::AccessControl, contract::ContractRuntimeContext};
use std::{cell::RefCell, rc::Rc};

pub struct UpdateHandler<R: ContractRuntimeContext + AccessControl, S: StateInterface> {
    runtime: Rc<RefCell<R>>,
    _state: S,

    owner: Account,
    application_id: ApplicationId,
    metadata: Metadata,
}

impl<R: ContractRuntimeContext + AccessControl, S: StateInterface> UpdateHandler<R, S> {
    pub fn new(runtime: Rc<RefCell<R>>, state: S, op: &AmsOperation) -> Self {
        let AmsOperation::Update {
            application_id,
            metadata,
        } = op
        else {
            panic!("Invalid operation");
        };
        let owner = runtime.borrow_mut().authenticated_account();

        Self {
            _state: state,
            runtime,

            owner,
            application_id: *application_id,
            metadata: metadata.clone(),
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl, S: StateInterface> Handler<AmsMessage, AmsResponse>
    for UpdateHandler<R, S>
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<AmsMessage, AmsResponse>>, HandlerError> {
        let destination = self.runtime.borrow_mut().application_creator_chain_id();
        let mut outcome = HandlerOutcome::new();

        outcome.with_message(
            destination,
            AmsMessage::Update {
                owner: self.owner,
                application_id: self.application_id,
                metadata: self.metadata.clone(),
            },
        );

        Ok(Some(outcome))
    }
}
