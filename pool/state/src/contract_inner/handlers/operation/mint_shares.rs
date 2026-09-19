use crate::interfaces::state::StateInterface;
use abi::pool::state_v1::{PoolStateV1Operation, PoolStateV1Response};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::{Account, Amount};
use runtime::interfaces::{access_control::AccessControl, contract::ContractRuntimeContext};
use std::{cell::RefCell, rc::Rc};

pub struct MintSharesHandler<R: ContractRuntimeContext + AccessControl, S: StateInterface> {
    runtime: Rc<RefCell<R>>,
    state: S,
    to: Account,
    amount: Amount,
}

impl<R: ContractRuntimeContext + AccessControl, S: StateInterface> MintSharesHandler<R, S> {
    pub fn new(runtime: Rc<RefCell<R>>, state: S, op: &PoolStateV1Operation) -> Self {
        let PoolStateV1Operation::MintShares { to, amount } = op else {
            panic!("Invalid operation");
        };
        Self {
            runtime,
            state,
            to: *to,
            amount: *amount,
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl, S: StateInterface> Handler<(), PoolStateV1Response>
    for MintSharesHandler<R, S>
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

        self.state
            .mint_shares(self.to, self.amount)
            .await
            .map_err(|error| HandlerError::ProcessError(Box::new(error)))?;

        let mut outcome = HandlerOutcome::new();
        outcome.with_response(PoolStateV1Response::Ok);
        Ok(Some(outcome))
    }
}
