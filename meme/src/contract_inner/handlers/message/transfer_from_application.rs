use crate::interfaces::state::StateInterface;
use abi::meme::{MemeMessage, MemeResponse};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::{Account, Amount};
use runtime::interfaces::{access_control::AccessControl, contract::ContractRuntimeContext};
use std::{cell::RefCell, rc::Rc};

pub struct TransferFromApplicationHandler<
    R: ContractRuntimeContext + AccessControl,
    S: StateInterface,
> {
    _runtime: Rc<RefCell<R>>,
    state: Rc<RefCell<S>>,

    caller: Account,
    to: Account,
    amount: Amount,
}

impl<R: ContractRuntimeContext + AccessControl, S: StateInterface>
    TransferFromApplicationHandler<R, S>
{
    pub fn new(runtime: Rc<RefCell<R>>, state: Rc<RefCell<S>>, msg: &MemeMessage) -> Self {
        let MemeMessage::TransferFromApplication { caller, to, amount } = msg else {
            panic!("Invalid message");
        };

        Self {
            state,
            _runtime: runtime,

            caller: *caller,
            to: *to,
            amount: *amount,
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl, S: StateInterface>
    Handler<MemeMessage, MemeResponse> for TransferFromApplicationHandler<R, S>
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<MemeMessage, MemeResponse>>, HandlerError> {
        self.state
            .borrow_mut()
            .transfer(self.caller, self.to, self.amount)
            .await
            .map_err(Into::into)?;

        Ok(None)
    }
}
