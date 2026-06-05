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
    runtime: Rc<RefCell<R>>,
    state: Rc<RefCell<S>>,

    caller: Account,
    to: Account,
    amount: Amount,
    receipt: TransferFromApplicationReceipt,
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
            runtime,
            state,
            caller: *caller,
            to: *to,
            amount: *amount,
            receipt: receipt.clone(),
        }
    }

    fn completed_receipt(&self, result: Result<(), String>) -> TransferFromApplicationReceipt {
        TransferFromApplicationReceipt {
            result: Some(result),
            ..self.receipt.clone()
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
        assert!(self.receipt.result.is_none(), "Invalid receipt result");
        assert!(self.receipt.amount == self.amount, "Invalid receipt amount");

        let mut outcome = HandlerOutcome::new();
        if self
            .runtime
            .borrow_mut()
            .message_is_bouncing()
            .unwrap_or(false)
        {
            outcome.with_message(
                self.caller.chain_id,
                MemeMessage::TransferFromApplicationReceipt {
                    caller: self.caller,
                    receipt: self.completed_receipt(Err(
                        "TransferFromApplicationWithReceipt bounced".to_string(),
                    )),
                },
                false,
            );
            return Ok(Some(outcome));
        }

        let result = self
            .state
            .borrow_mut()
            .transfer_ensure(self.caller, self.to, self.amount)
            .await
            .map_err(|err| err.to_string());

        outcome.with_message(
            self.caller.chain_id,
            MemeMessage::TransferFromApplicationReceipt {
                caller: self.caller,
                receipt: self.completed_receipt(result),
            },
            false,
        );

        Ok(Some(outcome))
    }
}
