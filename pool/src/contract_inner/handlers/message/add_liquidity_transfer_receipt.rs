use crate::interfaces::{parameters::ParametersInterface, state::StateInterface};
use abi::{
    meme_token::MemeToken,
    swap::pool::{AddLiquidityTransferReceipt, FundRequest, FundType, PoolMessage, PoolResponse},
};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::Amount;
use runtime::interfaces::{
    access_control::AccessControl, contract::ContractRuntimeContext, meme::MemeRuntimeContext,
};
use std::{cell::RefCell, rc::Rc};

pub struct AddLiquidityTransferReceiptHandler<
    R: ContractRuntimeContext + AccessControl + MemeRuntimeContext + ParametersInterface,
    S: StateInterface,
> {
    runtime: Rc<RefCell<R>>,
    state: Rc<RefCell<S>>,
    receipt: AddLiquidityTransferReceipt,
}

impl<R, S> AddLiquidityTransferReceiptHandler<R, S>
where
    R: ContractRuntimeContext + AccessControl + MemeRuntimeContext + ParametersInterface,
    S: StateInterface,
{
    pub fn new(runtime: Rc<RefCell<R>>, state: S, msg: &PoolMessage) -> Self {
        let PoolMessage::AddLiquidityTransferReceipt { receipt } = msg else {
            panic!("Invalid message");
        };

        Self {
            runtime,
            state: Rc::new(RefCell::new(state)),
            receipt: receipt.clone(),
        }
    }

    fn validate_source(&mut self) {
        let chain_id = self.runtime.borrow_mut().chain_id();
        let creator_chain_id = self.runtime.borrow_mut().application_creator_chain_id();
        assert_eq!(chain_id, creator_chain_id, "Invalid receipt chain");
    }

    fn validate_request(&self, request: &FundRequest) {
        assert!(request.amount_in > Amount::ZERO, "Invalid amount");
        assert_eq!(
            request.fund_type,
            FundType::AddLiquidity,
            "Invalid fund type"
        );

        let token = request.token.expect("Invalid fund token");
        self.state.borrow().pool().validate_token(Some(token));
    }

    fn request_2_message(&mut self, request: &FundRequest) -> PoolMessage {
        let token_0 = self.runtime.borrow_mut().token_0();
        let counterparty_amount_in = request
            .counterparty_amount_in
            .expect("Invalid counterparty amount");

        if request.token == Some(token_0) {
            PoolMessage::AddLiquidity {
                origin: request.from,
                amount_0_in: request.amount_in,
                amount_1_in: counterparty_amount_in,
                amount_0_out_min: request.amount_out_min,
                amount_1_out_min: request.counterparty_amount_out_min,
                to: request.to,
                block_timestamp: request.block_timestamp,
            }
        } else {
            PoolMessage::AddLiquidity {
                origin: request.from,
                amount_0_in: counterparty_amount_in,
                amount_1_in: request.amount_in,
                amount_0_out_min: request.counterparty_amount_out_min,
                amount_1_out_min: request.amount_out_min,
                to: request.to,
                block_timestamp: request.block_timestamp,
            }
        }
    }

    async fn credit_request(&mut self, request: &FundRequest) -> Result<(), HandlerError> {
        self.state
            .borrow_mut()
            .credit(
                MemeToken::from(request.token),
                request.from,
                request.amount_in,
            )
            .await
            .map_err(Into::into)
    }

    async fn settle_failed_transfer(&mut self) -> Result<(), HandlerError> {
        if let Some(prev) = self.receipt.prev.clone() {
            self.credit_request(&prev).await?;
        }

        Ok(())
    }

    fn settle_successful_transfer(&mut self) -> Option<HandlerOutcome<PoolMessage, PoolResponse>> {
        if self.receipt.next.is_some() {
            return None;
        }

        let request = self.receipt.request.clone();
        let message = self.request_2_message(&request);
        let mut outcome = HandlerOutcome::new();
        outcome.with_message(
            self.runtime.borrow_mut().application_creator_chain_id(),
            message,
            false,
        );

        Some(outcome)
    }
}

#[async_trait(?Send)]
impl<R, S> Handler<PoolMessage, PoolResponse> for AddLiquidityTransferReceiptHandler<R, S>
where
    R: ContractRuntimeContext + AccessControl + MemeRuntimeContext + ParametersInterface,
    S: StateInterface,
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<PoolMessage, PoolResponse>>, HandlerError> {
        self.validate_source();
        self.validate_request(&self.receipt.request);

        if self.receipt.result.is_err() {
            self.settle_failed_transfer().await?;
            return Ok(None);
        }

        Ok(self.settle_successful_transfer())
    }
}
