use crate::interfaces::{parameters::ParametersInterface, state::StateInterface};
use abi::swap::pool::{FundRequest, FundType, PoolMessage, PoolResponse, SwapTransferReceipt};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::Amount;
use runtime::interfaces::{
    access_control::AccessControl, contract::ContractRuntimeContext, meme::MemeRuntimeContext,
};
use std::{cell::RefCell, rc::Rc};

pub struct SwapTransferReceiptHandler<
    R: ContractRuntimeContext + AccessControl + MemeRuntimeContext + ParametersInterface,
    S: StateInterface,
> {
    runtime: Rc<RefCell<R>>,
    state: Rc<RefCell<S>>,
    receipt: SwapTransferReceipt,
}

impl<R, S> SwapTransferReceiptHandler<R, S>
where
    R: ContractRuntimeContext + AccessControl + MemeRuntimeContext + ParametersInterface,
    S: StateInterface,
{
    pub fn new(runtime: Rc<RefCell<R>>, state: S, msg: &PoolMessage) -> Self {
        let PoolMessage::SwapTransferReceipt { receipt } = msg else {
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

        let origin_chain_id = self.runtime.borrow_mut().message_origin_chain_id();
        assert_eq!(
            origin_chain_id,
            Some(self.receipt.request.from.chain_id),
            "Invalid receipt origin"
        );
    }

    fn validate_request(&self, request: &FundRequest) {
        assert!(request.amount_in > Amount::ZERO, "Invalid amount");
        assert_eq!(request.fund_type, FundType::Swap, "Invalid fund type");

        let token = request.token.expect("Invalid fund token");
        self.state.borrow().pool().validate_token(Some(token));
    }

    fn request_2_message(&mut self, request: &FundRequest) -> PoolMessage {
        let token = request.token.expect("Invalid fund token");
        let token_0 = self.runtime.borrow_mut().token_0();

        if token == token_0 {
            PoolMessage::Swap {
                origin: request.from,
                amount_0_in: Some(request.amount_in),
                amount_1_in: None,
                amount_0_out_min: None,
                amount_1_out_min: request.counterparty_amount_out_min,
                to: request.to,
                block_timestamp: request.block_timestamp,
            }
        } else {
            PoolMessage::Swap {
                origin: request.from,
                amount_0_in: None,
                amount_1_in: Some(request.amount_in),
                amount_0_out_min: request.counterparty_amount_out_min,
                amount_1_out_min: None,
                to: request.to,
                block_timestamp: request.block_timestamp,
            }
        }
    }

    fn settle_successful_transfer(&mut self) -> HandlerOutcome<PoolMessage, PoolResponse> {
        let request = self.receipt.request.clone();
        let message = self.request_2_message(&request);
        let mut outcome = HandlerOutcome::new();
        outcome.with_message(
            self.runtime.borrow_mut().application_creator_chain_id(),
            message,
            false,
        );
        outcome
    }
}

#[async_trait(?Send)]
impl<R, S> Handler<PoolMessage, PoolResponse> for SwapTransferReceiptHandler<R, S>
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
            return Ok(None);
        }

        Ok(Some(self.settle_successful_transfer()))
    }
}
