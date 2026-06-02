use crate::interfaces::{parameters::ParametersInterface, state::StateInterface};
use abi::swap::pool::{
    FundRequest, FundType, PoolMessage, PoolOperation, PoolResponse, SwapTransferReceipt,
};
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
    _state: Rc<RefCell<S>>,
    receipt: SwapTransferReceipt,
}

impl<R, S> SwapTransferReceiptHandler<R, S>
where
    R: ContractRuntimeContext + AccessControl + MemeRuntimeContext + ParametersInterface,
    S: StateInterface,
{
    pub fn new(runtime: Rc<RefCell<R>>, state: S, op: &PoolOperation) -> Self {
        let PoolOperation::SwapTransferReceipt { receipt } = op else {
            panic!("Invalid operation");
        };

        Self {
            runtime,
            _state: Rc::new(RefCell::new(state)),
            receipt: receipt.clone(),
        }
    }

    fn validate_source(&mut self) {
        let token = self.receipt.request.token.expect("Invalid fund token");
        assert_eq!(
            self.runtime.borrow_mut().chain_id(),
            self.receipt.request.from.chain_id,
            "Invalid swap transfer receipt chain"
        );
        assert_eq!(
            self.runtime.borrow_mut().authenticated_caller_id(),
            Some(token),
            "Invalid receipt caller"
        );
    }

    fn validate_request(&self, request: &FundRequest) {
        assert!(request.amount_in > Amount::ZERO, "Invalid amount");
        assert_eq!(request.fund_type, FundType::Swap, "Invalid fund type");
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

        let mut outcome = HandlerOutcome::new();
        outcome.with_message(
            self.runtime.borrow_mut().application_creator_chain_id(),
            PoolMessage::SwapTransferReceipt {
                receipt: self.receipt.clone(),
            },
            false,
        );

        Ok(Some(outcome))
    }
}
