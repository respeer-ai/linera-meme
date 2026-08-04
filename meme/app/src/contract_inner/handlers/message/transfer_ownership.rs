use crate::interfaces::state::StateInterface;
use abi::{application_state_base::PublicStateBaseInterface, meme::MemeMessage};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::Account;
use runtime::interfaces::{access_control::AccessControl, contract::ContractRuntimeContext};
use std::{cell::RefCell, rc::Rc};

pub struct TransferOwnershipHandler<
    R: ContractRuntimeContext + AccessControl,
    S: StateInterface + PublicStateBaseInterface,
> {
    _runtime: Rc<RefCell<R>>,
    state: S,

    owner: Account,
    new_owner: Account,
}

impl<R: ContractRuntimeContext + AccessControl, S: StateInterface + PublicStateBaseInterface>
    TransferOwnershipHandler<R, S>
{
    pub fn new(runtime: Rc<RefCell<R>>, state: S, message: &MemeMessage) -> Self {
        let MemeMessage::TransferOwnership { owner, new_owner } = message else {
            panic!("Invalid message");
        };

        Self {
            _runtime: runtime,
            state,
            owner: *owner,
            new_owner: *new_owner,
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl, S: StateInterface + PublicStateBaseInterface>
    Handler<abi::meme::MemeMessage, abi::meme::MemeResponse> for TransferOwnershipHandler<R, S>
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<abi::meme::MemeMessage, abi::meme::MemeResponse>>, HandlerError>
    {
        self.state
            .transfer_ownership(self.owner, self.new_owner)
            .await
            .map_err(|error| HandlerError::ProcessError(error.into()))?;

        Ok(None)
    }
}
