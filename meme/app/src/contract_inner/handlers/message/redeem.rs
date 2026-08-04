use crate::interfaces::state::StateInterface;
use abi::{application_state_base::PublicStateBaseInterface, meme::MemeMessage};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::{Account, Amount};
use runtime::interfaces::{access_control::AccessControl, contract::ContractRuntimeContext};
use std::{cell::RefCell, rc::Rc};

pub struct RedeemHandler<
    R: ContractRuntimeContext + AccessControl,
    S: StateInterface + PublicStateBaseInterface,
> {
    runtime: Rc<RefCell<R>>,
    state: S,
    owner: Account,
    amount: Option<Amount>,
}

impl<R: ContractRuntimeContext + AccessControl, S: StateInterface + PublicStateBaseInterface>
    RedeemHandler<R, S>
{
    pub fn new(runtime: Rc<RefCell<R>>, state: S, message: &MemeMessage) -> Self {
        let MemeMessage::Redeem { owner, amount } = message else {
            panic!("Invalid message");
        };

        Self {
            runtime,
            state,
            owner: *owner,
            amount: *amount,
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl, S: StateInterface + PublicStateBaseInterface>
    Handler<abi::meme::MemeMessage, abi::meme::MemeResponse> for RedeemHandler<R, S>
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<abi::meme::MemeMessage, abi::meme::MemeResponse>>, HandlerError>
    {
        let chain_id = self.runtime.borrow_mut().chain_id();
        let from = Account {
            chain_id,
            owner: self.owner.owner,
        };

        self.state
            .redeem(from, self.owner, self.amount)
            .await
            .map_err(|error| HandlerError::ProcessError(error.into()))?;

        Ok(None)
    }
}
