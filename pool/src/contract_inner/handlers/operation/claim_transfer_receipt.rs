use crate::interfaces::state::StateInterface;
use abi::swap::pool::{ClaimTransferReceipt, PoolMessage, PoolOperation, PoolResponse};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::Amount;
use runtime::interfaces::{
    access_control::AccessControl, contract::ContractRuntimeContext, meme::MemeRuntimeContext,
};
use std::{cell::RefCell, rc::Rc};

pub struct ClaimTransferReceiptHandler<
    R: ContractRuntimeContext + AccessControl + MemeRuntimeContext,
    S: StateInterface,
> {
    runtime: Rc<RefCell<R>>,
    state: S,
    receipt: ClaimTransferReceipt,
}

impl<R: ContractRuntimeContext + AccessControl + MemeRuntimeContext, S: StateInterface>
    ClaimTransferReceiptHandler<R, S>
{
    pub fn new(runtime: Rc<RefCell<R>>, state: S, op: &PoolOperation) -> Self {
        let PoolOperation::ClaimTransferReceipt { receipt } = op else {
            panic!("Invalid operation");
        };
        Self {
            runtime,
            state,
            receipt: receipt.clone(),
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl + MemeRuntimeContext, S: StateInterface>
    Handler<PoolMessage, PoolResponse> for ClaimTransferReceiptHandler<R, S>
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<PoolMessage, PoolResponse>>, HandlerError> {
        assert!(self.receipt.amount > Amount::ZERO, "Invalid amount");
        self.state.pool().validate_token(Some(self.receipt.token));
        assert!(
            self.runtime
                .borrow_mut()
                .authenticated_caller_id()
                .expect("Invalid claim transfer receipt caller")
                == self.receipt.token,
            "Invalid claim transfer receipt caller"
        );

        let destination = self.runtime.borrow_mut().application_creator_chain_id();
        let mut outcome = HandlerOutcome::new();
        outcome.with_message(
            destination,
            PoolMessage::ClaimTransferReceipt {
                receipt: self.receipt.clone(),
            },
        );

        Ok(Some(outcome))
    }
}
