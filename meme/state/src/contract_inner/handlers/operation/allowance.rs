use abi::meme::{MemeStateV1Operation, MemeStateV1Response};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::Account;
use runtime::interfaces::{access_control::AccessControl, contract::ContractRuntimeContext};
use std::{cell::RefCell, rc::Rc};

use crate::interfaces::state::StateInterface;

pub struct AllowanceHandler<S: StateInterface> {
    state: S,
    owner: Account,
    spender: Account,
}

impl<S: StateInterface> AllowanceHandler<S> {
    pub fn new<R: ContractRuntimeContext + AccessControl>(
        _runtime: Rc<RefCell<R>>,
        state: S,
        operation: &MemeStateV1Operation,
    ) -> Self {
        let MemeStateV1Operation::Allowance { owner, spender } = operation else {
            panic!("Invalid operation");
        };

        Self {
            state,
            owner: *owner,
            spender: *spender,
        }
    }
}

#[async_trait(?Send)]
impl<S: StateInterface> Handler<(), MemeStateV1Response> for AllowanceHandler<S> {
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<(), MemeStateV1Response>>, HandlerError> {
        let allowance = self
            .state
            .allowance_of(self.owner, self.spender)
            .await
            .map_err(|error| HandlerError::ProcessError(error.into()))?;

        let mut outcome = HandlerOutcome::new();
        outcome.with_response(MemeStateV1Response::Allowance(allowance));
        Ok(Some(outcome))
    }
}
