use crate::interfaces::state::StateInterface;
use abi::swap::SwapMessage;
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use runtime::interfaces::{access_control::AccessControl, contract::ContractRuntimeContext};
use std::{cell::RefCell, rc::Rc};

pub struct UpdatePoolHandler<R: ContractRuntimeContext + AccessControl, S: StateInterface> {
    _runtime: Rc<RefCell<R>>,
    state: S,

    token_0: ApplicationId,
    token_1: Option<ApplicationId>,
    transaction: Transaction,
    token_0_price: Amount,
    token_1_price: Amount,
    reserve_0: Amount,
    reserve_1: Amount,
}

impl<R: ContractRuntimeContext + AccessControl, S: StateInterface> UpdatePoolHandler<R, S> {
    pub fn new(runtime: Rc<RefCell<R>>, state: S, msg: &SwapMessage) -> Self {
        let SwapMessage::UpdatePool {
            token_0,
            token_1,
            transaction,
            token_0_price,
            token_1_price,
            reserve_0,
            reserve_1,
        } = msg
        else {
            panic!("Invalid message");
        };

        Self {
            state,
            _runtime: runtime,

            token_0: *token_0,
            token_1: *token_1,
            transaction: *transaction,
            token_0_price: *token_0_price,
            token_1_price: *token_1_price,
            reserve_0: *reserve_0,
            reserve_1: *reserve_1,
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl, S: StateInterface> Handler<SwapMessage>
    for UpdatePoolHandler<R, S>
{
    async fn handle(&mut self) -> Result<Option<HandlerOutcome<SwapMessage>>, HandlerError> {
        self.state
            .update_pool(
                token_0,
                token_1,
                transaction,
                token_0_price,
                token_1_price,
                reserve_0,
                reserve_1,
            )
            .await?;

        Ok(None)
    }
}
