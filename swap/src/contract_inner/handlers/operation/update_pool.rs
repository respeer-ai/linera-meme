use crate::interfaces::state::StateInterface;
use abi::swap::{
    router::{SwapMessage, SwapOperation, SwapResponse},
    transaction::Transaction,
};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::{Amount, ApplicationId};
use runtime::interfaces::{access_control::AccessControl, contract::ContractRuntimeContext};
use std::{cell::RefCell, rc::Rc};

pub struct UpdatePoolHandler<R: ContractRuntimeContext + AccessControl, S: StateInterface> {
    runtime: Rc<RefCell<R>>,
    _state: S,

    token_0: ApplicationId,
    token_1: Option<ApplicationId>,
    transaction: Transaction,
    token_0_price: Amount,
    token_1_price: Amount,
    reserve_0: Amount,
    reserve_1: Amount,
}

impl<R: ContractRuntimeContext + AccessControl, S: StateInterface> UpdatePoolHandler<R, S> {
    pub fn new(runtime: Rc<RefCell<R>>, state: S, op: &SwapOperation) -> Self {
        let SwapOperation::UpdatePool {
            token_0,
            token_1,
            transaction,
            token_0_price,
            token_1_price,
            reserve_0,
            reserve_1,
        } = op
        else {
            panic!("Invalid operation");
        };

        Self {
            _state: state,
            runtime,

            token_0: *token_0,
            token_1: *token_1,
            transaction: transaction.clone(),
            token_0_price: *token_0_price,
            token_1_price: *token_1_price,
            reserve_0: *reserve_0,
            reserve_1: *reserve_1,
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl, S: StateInterface>
    Handler<SwapMessage, SwapResponse> for UpdatePoolHandler<R, S>
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<SwapMessage, SwapResponse>>, HandlerError> {
        let destination = self.runtime.borrow_mut().application_creator_chain_id();
        let mut outcome = HandlerOutcome::new();

        outcome.with_message(
            destination,
            SwapMessage::UpdatePool {
                token_0: self.token_0,
                token_1: self.token_1,
                transaction: self.transaction.clone(),
                token_0_price: self.token_0_price,
                token_1_price: self.token_1_price,
                reserve_0: self.reserve_0,
                reserve_1: self.reserve_1,
            },
        );

        Ok(Some(outcome))
    }
}
