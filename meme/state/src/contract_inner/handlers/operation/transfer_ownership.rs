use abi::meme::{MemeStateV1Operation, MemeStateV1Response};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::Account;
use runtime::interfaces::{access_control::AccessControl, contract::ContractRuntimeContext};
use std::{cell::RefCell, rc::Rc};

use crate::interfaces::state::StateInterface;

pub struct TransferOwnershipHandler<R: ContractRuntimeContext + AccessControl, S: StateInterface> {
    runtime: Rc<RefCell<R>>,
    state: S,

    owner: Account,
    new_owner: Account,
}

impl<R: ContractRuntimeContext + AccessControl, S: StateInterface> TransferOwnershipHandler<R, S> {
    pub fn new(runtime: Rc<RefCell<R>>, state: S, operation: &MemeStateV1Operation) -> Self {
        let MemeStateV1Operation::TransferOwnership { owner, new_owner } = operation else {
            panic!("Invalid operation");
        };

        Self {
            runtime,
            state,
            owner: *owner,
            new_owner: *new_owner,
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl, S: StateInterface>
    Handler<(), MemeStateV1Response> for TransferOwnershipHandler<R, S>
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<(), MemeStateV1Response>>, HandlerError> {
        self.runtime
            .borrow_mut()
            .only_caller_creator()
            .map_err(|error| HandlerError::RuntimeError(error.into()))?;

        let caller = self
            .runtime
            .borrow_mut()
            .require_authenticated_caller_id()
            .map_err(|error| HandlerError::RuntimeError(error.into()))?;

        let business_application_id = self
            .state
            .business_application_id()
            .await
            .map_err(|error| HandlerError::ProcessError(error.into()))?;
        if caller != business_application_id {
            return Err(HandlerError::NotAllowed);
        }

        self.state
            .transfer_ownership(self.owner, self.new_owner)
            .await
            .map_err(|error| HandlerError::ProcessError(error.into()))?;

        let mut outcome = HandlerOutcome::new();
        outcome.with_response(MemeStateV1Response::Ok);
        Ok(Some(outcome))
    }
}
