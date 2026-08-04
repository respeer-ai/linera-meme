use crate::interfaces::state::StateInterface;
use abi::{application_state_base::PublicStateBaseInterface, meme::MemeMessage};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::{Account, Amount};
use runtime::interfaces::{access_control::AccessControl, contract::ContractRuntimeContext};
use std::{cell::RefCell, rc::Rc};

pub struct TransferFromApplicationHandler<
    R: ContractRuntimeContext + AccessControl,
    S: StateInterface + PublicStateBaseInterface,
> {
    _runtime: Rc<RefCell<R>>,
    state: S,
    caller: Account,
    to: Account,
    amount: Amount,
}

impl<R: ContractRuntimeContext + AccessControl, S: StateInterface + PublicStateBaseInterface>
    TransferFromApplicationHandler<R, S>
{
    pub fn new(_runtime: Rc<RefCell<R>>, state: S, message: &MemeMessage) -> Self {
        let MemeMessage::TransferFromApplication { caller, to, amount } = message else {
            panic!("Invalid message");
        };

        Self {
            _runtime,
            state,
            caller: *caller,
            to: *to,
            amount: *amount,
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl, S: StateInterface + PublicStateBaseInterface>
    Handler<abi::meme::MemeMessage, abi::meme::MemeResponse>
    for TransferFromApplicationHandler<R, S>
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<abi::meme::MemeMessage, abi::meme::MemeResponse>>, HandlerError>
    {
        self.state
            .transfer_from_application(self.caller, self.to, self.amount)
            .await
            .map_err(|error| HandlerError::ProcessError(error.into()))?;

        Ok(None)
    }
}
