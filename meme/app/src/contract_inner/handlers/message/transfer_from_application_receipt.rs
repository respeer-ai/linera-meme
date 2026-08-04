use crate::interfaces::state::StateInterface;
use abi::{
    meme::{
        MemeMessage, MemeResponse, TransferFromApplicationReceipt,
        TransferFromApplicationReceiptPayload, TransferFromApplicationReceiptPurpose,
    },
    swap::pool::{
        AddLiquidityTransferReceipt, ClaimTransferReceipt, FundType, PoolAbi, PoolOperation,
        SwapTransferReceipt,
    },
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
    _state: S,
    caller: Account,
    receipt: TransferFromApplicationReceipt,
}

impl<R: ContractRuntimeContext + AccessControl, S: StateInterface>
    TransferFromApplicationReceiptHandler<R, S>
{
    pub fn new(runtime: Rc<RefCell<R>>, state: S, msg: &MemeMessage) -> Self {
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
        if self
            .runtime
            .borrow_mut()
            .message_is_bouncing()
            .unwrap_or(false)
        {
            return Ok(None);
        }

        assert_eq!(
            self.runtime.borrow_mut().chain_id(),
            self.caller.chain_id,
            "Invalid receipt chain"
        );

        let Some(result) = self.receipt.result.clone() else {
            panic!("Invalid receipt result");
        };

        match self.receipt.purpose {
            TransferFromApplicationReceiptPurpose::PoolClaim => {
                assert!(self.receipt.payload.is_none(), "Invalid receipt payload");

                let AccountOwner::Address32(application_description_hash) = self.caller.owner else {
                    panic!("Invalid receipt caller");
                };
                let pool_application: ApplicationId = ApplicationId::new(application_description_hash);
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
            TransferFromApplicationReceiptPurpose::PoolAddLiquidity => {
                let Some(TransferFromApplicationReceiptPayload::PoolAddLiquidity(payload)) =
                    self.receipt.payload.clone()
                else {
                    panic!("Invalid receipt payload");
                };

                assert_eq!(self.receipt.owner, payload.request.from, "Invalid receipt owner");
                assert_eq!(
                    Some(self.receipt.token),
                    payload.request.token,
                    "Invalid receipt token"
                );
                assert_eq!(
                    self.receipt.amount, payload.request.amount_in,
                    "Invalid receipt amount"
                );
                assert_eq!(
                    payload.request.fund_type,
                    FundType::AddLiquidity,
                    "Invalid fund type"
                );

                let AccountOwner::Address32(application_description_hash) = self.caller.owner else {
                    panic!("Invalid receipt caller");
                };
                let pool_application: ApplicationId = ApplicationId::new(application_description_hash);
                let operation = PoolOperation::AddLiquidityTransferReceipt {
                    receipt: AddLiquidityTransferReceipt {
                        result,
                        prev: payload.prev,
                        request: payload.request,
                        next: payload.next,
                    },
                };
                let _ = self
                    .runtime
                    .borrow_mut()
                    .call_application(pool_application.with_abi::<PoolAbi>(), &operation);
            }
            TransferFromApplicationReceiptPurpose::PoolSwap => {
                let Some(TransferFromApplicationReceiptPayload::PoolSwap(payload)) =
                    self.receipt.payload.clone()
                else {
                    panic!("Invalid receipt payload");
                };

                assert_eq!(self.receipt.owner, payload.request.from, "Invalid receipt owner");
                assert_eq!(
                    Some(self.receipt.token),
                    payload.request.token,
                    "Invalid receipt token"
                );
                assert_eq!(
                    self.receipt.amount, payload.request.amount_in,
                    "Invalid receipt amount"
                );
                assert_eq!(payload.request.fund_type, FundType::Swap, "Invalid fund type");

                let AccountOwner::Address32(application_description_hash) = self.caller.owner else {
                    panic!("Invalid receipt caller");
                };
                let pool_application: ApplicationId = ApplicationId::new(application_description_hash);
                let operation = PoolOperation::SwapTransferReceipt {
                    receipt: SwapTransferReceipt {
                        result,
                        request: payload.request,
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
