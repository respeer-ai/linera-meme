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
        if self
            .runtime
            .borrow_mut()
            .message_is_bouncing()
            .unwrap_or(false)
        {
            // A bounced TransferFromApplicationReceipt means the receipt message was
            // rejected while being delivered back to the pool chain. Linera exposes only
            // `message_is_bouncing`; it does not expose the original reject reason to this
            // handler.
            //
            // Normal claim path covered by the protocol:
            // - If the pool chain does not process the tracked receipt yet, the message
            //   stays pending; it is not skipped and is not a bounce.
            // - A valid success receipt calls PoolOperation::ClaimTransferReceipt and
            //   consumes the matching claiming balance.
            // - A valid failure receipt calls PoolOperation::ClaimTransferReceipt and
            //   restores the matching claiming balance to claimable balance.
            //
            // Rejects caused by malformed input or attack:
            // - `receipt.result == None`: an incomplete request receipt was sent back as a
            //   completed receipt.
            // - `caller.owner` is not `AccountOwner::Address32`: the caller cannot encode a
            //   pool application id.
            // - `caller.owner` encodes a non-pool or wrong pool application: the
            //   call_application target rejects or does not implement the expected ABI.
            // - `receipt.token` is not one of the pool tokens.
            // - `authenticated_caller_id()` in the pool operation is not `receipt.token`:
            //   a non-token application tried to settle the claim.
            // - `receipt.amount == 0`.
            // - `claiming_balances[receipt.token][receipt.owner] < receipt.amount`: this
            //   covers forged owner, forged amount, duplicate receipt after settlement,
            //   stale receipt, and receipt without a matching prior claim.
            //
            // Rejects caused by implementation, deployment, or operator failure:
            // - handler bug or assertion bug;
            // - ABI mismatch between meme and pool;
            // - legal receipt exceeds configured execution resource limits;
            // - execution fee funding is insufficient;
            // - node policy explicitly rejects the message.
            //
            // No recovery is performed in this bounced branch. For a success receipt, the
            // user has already received the meme token and the pool amount remains locked in
            // claiming_balances, so it cannot be claimed again. A bounced failure receipt is
            // outside the normal protocol path and remains locked for operator/projection
            // diagnosis.
            return Ok(None);
        }

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
