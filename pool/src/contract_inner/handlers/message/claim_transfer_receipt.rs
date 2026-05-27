use crate::interfaces::state::StateInterface;
use abi::{
    meme_token::MemeToken,
    swap::pool::{ClaimTransferReceipt, PoolMessage, PoolResponse},
};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::Amount;
use runtime::interfaces::{access_control::AccessControl, contract::ContractRuntimeContext};
use std::{cell::RefCell, rc::Rc};

pub struct ClaimTransferReceiptHandler<R: ContractRuntimeContext + AccessControl, S: StateInterface>
{
    _runtime: Rc<RefCell<R>>,
    state: S,
    receipt: ClaimTransferReceipt,
}

impl<R: ContractRuntimeContext + AccessControl, S: StateInterface>
    ClaimTransferReceiptHandler<R, S>
{
    pub fn new(runtime: Rc<RefCell<R>>, state: S, msg: &PoolMessage) -> Self {
        let PoolMessage::ClaimTransferReceipt { receipt } = msg else {
            panic!("Invalid message");
        };

        Self {
            _runtime: runtime,
            state,
            receipt: receipt.clone(),
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl, S: StateInterface>
    Handler<PoolMessage, PoolResponse> for ClaimTransferReceiptHandler<R, S>
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<PoolMessage, PoolResponse>>, HandlerError> {
        assert!(self.receipt.amount > Amount::ZERO, "Invalid amount");
        self.state.pool().validate_token(Some(self.receipt.token));

        let token = MemeToken::Fungible(self.receipt.token);
        match self.receipt.result {
            Ok(()) => {
                self.state
                    .claim_success(token, self.receipt.owner, self.receipt.amount)
                    .await
                    .map_err(Into::into)?;
            }
            Err(_) => {
                self.state
                    .claim_fail(token, self.receipt.owner, self.receipt.amount)
                    .await
                    .map_err(Into::into)?;
            }
        }

        Ok(None)
    }
}
