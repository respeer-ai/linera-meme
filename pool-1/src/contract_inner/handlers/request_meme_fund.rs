use crate::interfaces::state::StateInterface;
use abi::swap::pool::PoolMessage;
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::{Amount, ApplicationId};
use runtime::interfaces::{
    access_control::AccessControl, contract::ContractRuntimeContext, meme::MemeRuntimeContext,
};
use std::{cell::RefCell, rc::Rc};

pub struct RequestMemeFundHandler<
    R: ContractRuntimeContext + AccessControl + MemeRuntimeContext,
    S: StateInterface,
> {
    runtime: Rc<RefCell<R>>,
    _state: Rc<RefCell<S>>,

    token: ApplicationId,
    amount: Amount,
    transfer_id: u64,
}

impl<R: ContractRuntimeContext + AccessControl + MemeRuntimeContext, S: StateInterface>
    RequestMemeFundHandler<R, S>
{
    pub fn new(
        runtime: Rc<RefCell<R>>,
        state: Rc<RefCell<S>>,
        token: ApplicationId,
        amount: Amount,
        transfer_id: u64,
    ) -> Self {
        Self {
            _state: state,
            runtime,

            token,
            amount,
            transfer_id,
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl + MemeRuntimeContext, S: StateInterface>
    Handler<PoolMessage> for RequestMemeFundHandler<R, S>
{
    async fn handle(&mut self) -> Result<Option<HandlerOutcome<PoolMessage>>, HandlerError> {
        let mut runtime_context = self.runtime.borrow_mut();
        let destination = runtime_context
            .token_creator_chain_id(self.token)
            .expect("Failed: token creator chain id");
        let mut outcome = HandlerOutcome::new();

        outcome.with_message(
            destination,
            PoolMessage::RequestFund {
                token: self.token,
                transfer_id: self.transfer_id,
                amount: self.amount,
            },
        );

        Ok(Some(outcome))
    }
}
