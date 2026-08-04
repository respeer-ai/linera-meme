use crate::interfaces::state::StateInterface;
use abi::{
    application_state_base::PublicStateBaseInterface,
    meme::{MemeMessage, MemeOperation, MemeResponse},
};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::Amount;
use runtime::interfaces::{access_control::AccessControl, contract::ContractRuntimeContext};
use std::{cell::RefCell, rc::Rc};

pub struct TransferToCallerHandler<R, S> {
    runtime: Rc<RefCell<R>>,
    state: S,
    amount: Amount,
}

impl<R: ContractRuntimeContext + AccessControl, S: StateInterface + PublicStateBaseInterface>
    TransferToCallerHandler<R, S>
{
    pub fn new(runtime: Rc<RefCell<R>>, state: S, op: &MemeOperation) -> Self {
        let MemeOperation::TransferToCaller { amount } = op else {
            panic!("Invalid operation");
        };
        Self {
            runtime,
            state,
            amount: *amount,
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl, S: StateInterface + PublicStateBaseInterface>
    Handler<MemeMessage, MemeResponse> for TransferToCallerHandler<R, S>
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<MemeMessage, MemeResponse>>, HandlerError> {
        let caller = self.runtime.borrow_mut().message_caller_account();
        let from = self.runtime.borrow_mut().message_signer_account();
        let mut outcome = HandlerOutcome::new();
        match self
            .state
            .transfer(from, caller, self.amount)
            .await
            .map_err(|error| HandlerError::ProcessError(error.into()))
        {
            Ok(_) => {}
            Err(err) => {
                outcome.with_response(MemeResponse::Fail(err.to_string()));
            }
        }
        Ok(Some(outcome))
    }
}
