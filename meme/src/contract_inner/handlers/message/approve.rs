use crate::interfaces::state::StateInterface;
use abi::meme::{MemeMessage, MemeResponse};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::{Account, Amount};
use runtime::interfaces::{
    access_control::AccessControl, contract::ContractRuntimeContext, meme::MemeRuntimeContext,
};
use std::{cell::RefCell, rc::Rc};

pub struct ApproveHandler<
    R: ContractRuntimeContext + AccessControl + MemeRuntimeContext,
    S: StateInterface,
> {
    _runtime: Rc<RefCell<R>>,
    state: S,

    owner: Account,
    spender: Account,
    amount: Amount,
}

impl<R: ContractRuntimeContext + AccessControl + MemeRuntimeContext, S: StateInterface>
    ApproveHandler<R, S>
{
    pub fn new(runtime: Rc<RefCell<R>>, state: S, msg: &MemeMessage) -> Self {
        let MemeMessage::Approve {
            owner,
            spender,
            amount,
        } = msg
        else {
            panic!("Invalid message");
        };

        Self {
            state,
            _runtime: runtime,

            owner: *owner,
            spender: *spender,
            amount: *amount,
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl + MemeRuntimeContext, S: StateInterface>
    Handler<MemeMessage, MemeResponse> for ApproveHandler<R, S>
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<MemeMessage, MemeResponse>>, HandlerError> {
        let balance = self.state.balance_of(self.owner).await;
        assert!(self.amount <= balance, "Insufficient balance");

        self.state
            .approve(self.owner, self.spender, self.amount)
            .await
            .map_err(Into::into)?;

        Ok(None)
    }
}
