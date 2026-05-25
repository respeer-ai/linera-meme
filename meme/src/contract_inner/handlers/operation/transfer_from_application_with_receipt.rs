use crate::interfaces::state::StateInterface;
use abi::meme::{MemeMessage, MemeOperation, MemeResponse, TransferFromApplicationReceipt};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::{Account, Amount};
use runtime::interfaces::{
    access_control::AccessControl, contract::ContractRuntimeContext, meme::MemeRuntimeContext,
};
use std::{cell::RefCell, rc::Rc};

pub struct TransferFromApplicationWithReceiptHandler<
    R: ContractRuntimeContext + AccessControl + MemeRuntimeContext,
    S: StateInterface,
> {
    _runtime: Rc<RefCell<R>>,
    _state: Rc<RefCell<S>>,

    _to: Account,
    _amount: Amount,
    _receipt: TransferFromApplicationReceipt,
}

impl<R: ContractRuntimeContext + AccessControl + MemeRuntimeContext, S: StateInterface>
    TransferFromApplicationWithReceiptHandler<R, S>
{
    pub fn new(runtime: Rc<RefCell<R>>, state: Rc<RefCell<S>>, op: &MemeOperation) -> Self {
        let MemeOperation::TransferFromApplicationWithReceipt {
            to,
            amount,
            receipt,
        } = op
        else {
            panic!("Invalid operation");
        };

        Self {
            _runtime: runtime,
            _state: state,

            _to: *to,
            _amount: *amount,
            _receipt: *receipt,
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl + MemeRuntimeContext, S: StateInterface>
    Handler<MemeMessage, MemeResponse> for TransferFromApplicationWithReceiptHandler<R, S>
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<MemeMessage, MemeResponse>>, HandlerError> {
        panic!("TransferFromApplicationWithReceipt operation is not implemented yet")
    }
}
