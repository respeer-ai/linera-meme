use crate::interfaces::state::StateInterface;
use abi::swap::pool::{PoolMessage, PoolOperation, PoolResponse};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::{Amount, ApplicationId};
use runtime::interfaces::{
    access_control::AccessControl, contract::ContractRuntimeContext, meme::MemeRuntimeContext,
};
use std::{cell::RefCell, marker::PhantomData, rc::Rc};

pub struct ClaimHandler<
    R: ContractRuntimeContext + AccessControl + MemeRuntimeContext,
    S: StateInterface,
> {
    runtime: Rc<RefCell<R>>,

    token: Option<ApplicationId>,
    amount: Amount,
    _state: PhantomData<S>,
}

impl<R: ContractRuntimeContext + AccessControl + MemeRuntimeContext, S: StateInterface>
    ClaimHandler<R, S>
{
    pub fn new(runtime: Rc<RefCell<R>>, _state: S, op: &PoolOperation) -> Self {
        let PoolOperation::Claim { token, amount } = op else {
            panic!("Invalid operation");
        };

        Self {
            runtime,

            token: *token,
            amount: *amount,
            _state: PhantomData,
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl + MemeRuntimeContext, S: StateInterface>
    Handler<PoolMessage, PoolResponse> for ClaimHandler<R, S>
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<PoolMessage, PoolResponse>>, HandlerError> {
        assert!(self.amount > Amount::ZERO, "Invalid amount");

        let origin = self.runtime.borrow_mut().authenticated_account();
        let destination = self.runtime.borrow_mut().application_creator_chain_id();
        let mut outcome = HandlerOutcome::new();
        outcome.with_message(
            destination,
            PoolMessage::Claim {
                origin,
                token: self.token,
                amount: self.amount,
            },
            false,
        );

        Ok(Some(outcome))
    }
}
