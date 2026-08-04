use crate::interfaces::state::StateInterface;
use abi::{application_state_base::PublicStateBaseInterface, meme::MemeMessage};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::{Account, Amount};
use runtime::interfaces::{access_control::AccessControl, contract::ContractRuntimeContext};
use std::{cell::RefCell, rc::Rc};

pub struct MintHandler<
    R: ContractRuntimeContext + AccessControl,
    S: StateInterface + PublicStateBaseInterface,
> {
    runtime: Rc<RefCell<R>>,
    state: S,
    to: Account,
    amount: Amount,
}

impl<R: ContractRuntimeContext + AccessControl, S: StateInterface + PublicStateBaseInterface>
    MintHandler<R, S>
{
    pub fn new(runtime: Rc<RefCell<R>>, state: S, message: &MemeMessage) -> Self {
        let MemeMessage::Mint { to, amount } = message else {
            panic!("Invalid message");
        };

        Self {
            runtime,
            state,
            to: *to,
            amount: *amount,
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl, S: StateInterface + PublicStateBaseInterface>
    Handler<abi::meme::MemeMessage, abi::meme::MemeResponse> for MintHandler<R, S>
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<abi::meme::MemeMessage, abi::meme::MemeResponse>>, HandlerError>
    {
        let signer = self
            .runtime
            .borrow_mut()
            .authenticated_signer()
            .ok_or(HandlerError::NotAllowed)?;
        let owner = self
            .state
            .owner()
            .await
            .map_err(|error| HandlerError::ProcessError(error.into()))?;
        if signer != owner.owner {
            return Err(HandlerError::NotAllowed);
        }

        self.state
            .mint(self.to, self.amount)
            .await
            .map_err(|error| HandlerError::ProcessError(error.into()))?;

        Ok(None)
    }
}
