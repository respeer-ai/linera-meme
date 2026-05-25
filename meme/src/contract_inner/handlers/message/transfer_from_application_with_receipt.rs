use crate::interfaces::state::StateInterface;
use abi::meme::{MemeMessage, MemeResponse, TransferFromApplicationReceipt};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::{Account, Amount};
use runtime::interfaces::{access_control::AccessControl, contract::ContractRuntimeContext};
use std::{cell::RefCell, rc::Rc};

pub struct TransferFromApplicationWithReceiptHandler<
    R: ContractRuntimeContext + AccessControl,
    S: StateInterface,
> {
    _runtime: Rc<RefCell<R>>,
    _state: Rc<RefCell<S>>,

    _caller: Account,
    _to: Account,
    _amount: Amount,
    _receipt: TransferFromApplicationReceipt,
}

impl<R: ContractRuntimeContext + AccessControl, S: StateInterface>
    TransferFromApplicationWithReceiptHandler<R, S>
{
    pub fn new(runtime: Rc<RefCell<R>>, state: Rc<RefCell<S>>, msg: &MemeMessage) -> Self {
        let MemeMessage::TransferFromApplicationWithReceipt {
            caller,
            to,
            amount,
            receipt,
        } = msg
        else {
            panic!("Invalid message");
        };

        Self {
            _runtime: runtime,
            _state: state,

            _caller: *caller,
            _to: *to,
            _amount: *amount,
            _receipt: *receipt,
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl, S: StateInterface>
    Handler<MemeMessage, MemeResponse> for TransferFromApplicationWithReceiptHandler<R, S>
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<MemeMessage, MemeResponse>>, HandlerError> {
        panic!("TransferFromApplicationWithReceipt message is not implemented yet")
    }
}
