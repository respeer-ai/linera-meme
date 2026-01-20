use crate::interfaces::{parameters::ParametersInterface, state::StateInterface};
use abi::meme::{MemeMessage, MemeOperation, MemeResponse};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::Amount;
use runtime::interfaces::{
    access_control::AccessControl, contract::ContractRuntimeContext, meme::MemeRuntimeContext,
};
use std::{cell::RefCell, rc::Rc};

pub struct RedeemHandler<
    R: ContractRuntimeContext + AccessControl + MemeRuntimeContext + ParametersInterface,
    S: StateInterface,
> {
    runtime: Rc<RefCell<R>>,
    _state: S,

    amount: Option<Amount>,
}

impl<
        R: ContractRuntimeContext + AccessControl + MemeRuntimeContext + ParametersInterface,
        S: StateInterface,
    > RedeemHandler<R, S>
{
    pub fn new(runtime: Rc<RefCell<R>>, state: S, op: &MemeOperation) -> Self {
        let MemeOperation::Redeem { amount } = op else {
            panic!("Invalid operation");
        };

        Self {
            _state: state,
            runtime,

            amount: *amount,
        }
    }
}

#[async_trait(?Send)]
impl<
        R: ContractRuntimeContext + AccessControl + MemeRuntimeContext + ParametersInterface,
        S: StateInterface,
    > Handler<MemeMessage, MemeResponse> for RedeemHandler<R, S>
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<MemeMessage, MemeResponse>>, HandlerError> {
        let destination = self.runtime.borrow_mut().application_creator_chain_id();
        let mut outcome = HandlerOutcome::new();

        let owner = self.runtime.borrow_mut().authenticated_account();

        outcome.with_message(
            destination,
            MemeMessage::Redeem {
                owner,
                amount: self.amount,
            },
        );

        Ok(Some(outcome))
    }
}
