use crate::interfaces::state::StateInterface;
use abi::pool::state_v1::{PoolStateV1Operation, PoolStateV1Response};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::{Account, ApplicationId};
use runtime::interfaces::{access_control::AccessControl, contract::ContractRuntimeContext};
use std::{cell::RefCell, rc::Rc};

pub struct ClaimableBalanceHandler<R: ContractRuntimeContext + AccessControl, S: StateInterface> {
    runtime: Rc<RefCell<R>>,
    state: S,
    token: Option<ApplicationId>,
    owner: Account,
}

impl<R: ContractRuntimeContext + AccessControl, S: StateInterface> ClaimableBalanceHandler<R, S> {
    pub fn new(runtime: Rc<RefCell<R>>, state: S, op: &PoolStateV1Operation) -> Self {
        let PoolStateV1Operation::ClaimableBalance { token, owner } = op else {
            panic!("Invalid operation");
        };
        Self {
            runtime,
            state,
            token: *token,
            owner: *owner,
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl, S: StateInterface> Handler<(), PoolStateV1Response>
    for ClaimableBalanceHandler<R, S>
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<(), PoolStateV1Response>>, HandlerError> {
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

        let balance = self
            .state
            .claimable_balance(self.token, self.owner)
            .await
            .map_err(|error| HandlerError::ProcessError(Box::new(error)))?;

        let mut outcome = HandlerOutcome::new();
        outcome.with_response(PoolStateV1Response::ClaimableBalance(balance));
        Ok(Some(outcome))
    }
}
