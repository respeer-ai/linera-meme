use crate::interfaces::state::StateInterface;
use abi::meme::{MemeMessage, MemeOperation, MemeResponse, TransferFromApplicationReceipt};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::{Account, AccountOwner, Amount};
use runtime::interfaces::{
    access_control::AccessControl, contract::ContractRuntimeContext, meme::MemeRuntimeContext,
};
use std::{cell::RefCell, rc::Rc};

pub struct TransferFromApplicationWithReceiptHandler<
    R: ContractRuntimeContext + AccessControl + MemeRuntimeContext,
    S: StateInterface,
> {
    runtime: Rc<RefCell<R>>,
    _state: Rc<RefCell<S>>,

    to: Account,
    amount: Amount,
    receipt: TransferFromApplicationReceipt,
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
            runtime,
            _state: state,
            to: *to,
            amount: *amount,
            receipt: receipt.clone(),
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
        assert!(self.receipt.result.is_none(), "Invalid receipt result");
        assert!(self.receipt.amount == self.amount, "Invalid receipt amount");

        let destination = self.runtime.borrow_mut().application_creator_chain_id();
        let caller_id = self.runtime.borrow_mut().authenticated_caller_id().unwrap();
        let chain_id = self.runtime.borrow_mut().chain_id();
        let caller = Account {
            chain_id,
            owner: AccountOwner::from(caller_id),
        };

        let mut outcome = HandlerOutcome::new();
        outcome.with_message(
            destination,
            MemeMessage::TransferFromApplicationWithReceipt {
                caller,
                to: self.to,
                amount: self.amount,
                receipt: self.receipt.clone(),
            },
            true,
        );

        Ok(Some(outcome))
    }
}
