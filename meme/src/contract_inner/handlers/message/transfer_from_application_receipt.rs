use crate::interfaces::state::StateInterface;
use abi::{
    meme::{
        MemeMessage, MemeResponse, TransferFromApplicationReceipt,
        TransferFromApplicationReceiptPurpose,
    },
    swap::pool::{ClaimTransferReceipt, PoolAbi, PoolOperation},
};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::{Account, AccountOwner, ApplicationId};
use runtime::interfaces::{access_control::AccessControl, contract::ContractRuntimeContext};
use std::{cell::RefCell, rc::Rc};

pub struct TransferFromApplicationReceiptHandler<
    R: ContractRuntimeContext + AccessControl,
    S: StateInterface,
> {
    runtime: Rc<RefCell<R>>,
    _state: Rc<RefCell<S>>,
    caller: Account,
    receipt: TransferFromApplicationReceipt,
}

impl<R: ContractRuntimeContext + AccessControl, S: StateInterface>
    TransferFromApplicationReceiptHandler<R, S>
{
    pub fn new(runtime: Rc<RefCell<R>>, state: Rc<RefCell<S>>, msg: &MemeMessage) -> Self {
        let MemeMessage::TransferFromApplicationReceipt { caller, receipt } = msg else {
            panic!("Invalid message");
        };
        Self {
            runtime,
            _state: state,
            caller: *caller,
            receipt: receipt.clone(),
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl, S: StateInterface>
    Handler<MemeMessage, MemeResponse> for TransferFromApplicationReceiptHandler<R, S>
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<MemeMessage, MemeResponse>>, HandlerError> {
        let Some(result) = self.receipt.result.clone() else {
            panic!("Invalid receipt result");
        };

        match self.receipt.purpose {
            TransferFromApplicationReceiptPurpose::PoolClaim => {
                let AccountOwner::Address32(application_description_hash) = self.caller.owner
                else {
                    panic!("Invalid receipt caller");
                };
                let pool_application: ApplicationId =
                    ApplicationId::new(application_description_hash);
                let operation = PoolOperation::ClaimTransferReceipt {
                    receipt: ClaimTransferReceipt {
                        owner: self.receipt.owner,
                        token: self.receipt.token,
                        amount: self.receipt.amount,
                        result,
                    },
                };
                let _ = self
                    .runtime
                    .borrow_mut()
                    .call_application(pool_application.with_abi::<PoolAbi>(), &operation);
            }
        }

        Ok(None)
    }
}
