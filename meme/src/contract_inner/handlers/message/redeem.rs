use crate::interfaces::state::StateInterface;
use abi::meme::{MemeMessage, MemeResponse};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::{Account, Amount};
use runtime::interfaces::{
    access_control::AccessControl, contract::ContractRuntimeContext, meme::MemeRuntimeContext,
};
use std::{cell::RefCell, rc::Rc};

pub struct RedeemHandler<
    R: ContractRuntimeContext + AccessControl + MemeRuntimeContext,
    S: StateInterface,
> {
    runtime: Rc<RefCell<R>>,
    state: Rc<RefCell<S>>,

    owner: Account,
    amount: Option<Amount>,
}

impl<R: ContractRuntimeContext + AccessControl + MemeRuntimeContext, S: StateInterface>
    RedeemHandler<R, S>
{
    pub fn new(runtime: Rc<RefCell<R>>, state: Rc<RefCell<S>>, msg: &MemeMessage) -> Self {
        let MemeMessage::Redeem { owner, amount } = msg else {
            panic!("Invalid message");
        };

        Self {
            state,
            runtime,

            owner: *owner,
            amount: *amount,
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl + MemeRuntimeContext, S: StateInterface>
    Handler<MemeMessage, MemeResponse> for RedeemHandler<R, S>
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<MemeMessage, MemeResponse>>, HandlerError> {
        let chain_id = self.runtime.borrow_mut().chain_id();
        let from = Account {
            chain_id,
            owner: self.owner.owner,
        };
        let amount = self
            .amount
            .unwrap_or(self.state.borrow().balance_of(from).await);

        self.state
            .borrow_mut()
            .transfer(from, self.owner, amount)
            .await
            .map_err(Into::into)?;

        Ok(None)
    }
}
