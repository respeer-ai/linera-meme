use crate::{
    contract_inner::handlers::{
        fund_pool_application_creation_chain::FundPoolApplicationCreationChainHandler,
        request_meme_fund::RequestMemeFundExtHandler,
    },
    interfaces::{parameters::ParametersInterface, state::StateInterface},
};
use abi::swap::pool::{
    AddLiquidityTransferReceipt, FundRequest, FundType, PoolMessage, PoolOperation, PoolResponse,
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
    pub fn new(runtime: Rc<RefCell<R>>, state: S, op: &PoolOperation) -> Self {
        let PoolOperation::AddLiquidityTransferReceipt { receipt } = op else {
            panic!("Invalid operation");
        };

        Self {
            runtime,
            state: Rc::new(RefCell::new(state)),
            receipt: receipt.clone(),
        }
    }

    fn validate_source(&mut self) {
        let token = self.receipt.request.token.expect("Invalid fund token");
        let chain_id = self.runtime.borrow_mut().chain_id();
        assert_eq!(
            chain_id, self.receipt.request.from.chain_id,
            "Invalid add liquidity transfer receipt chain"
        );
        assert_eq!(
            self.runtime.borrow_mut().authenticated_caller_id(),
            Some(token),
            "Invalid receipt caller"
        );
    }

    fn validate_request(&self, request: &FundRequest) {
        assert!(request.amount_in > Amount::ZERO, "Invalid amount");
        assert_eq!(
            request.fund_type,
            FundType::AddLiquidity,
            "Invalid fund type"
        );
    }

    async fn transfer_native(&mut self, amount: Amount) {
        let _ = FundPoolApplicationCreationChainHandler::new(
            self.runtime.clone(),
            self.state.clone(),
            amount,
        )
        .handle()
        .await;
    }

    fn final_settlement_receipt(&self) -> AddLiquidityTransferReceipt {
        AddLiquidityTransferReceipt {
            result: self.receipt.result.clone(),
            prev: self.receipt.prev.clone(),
            request: self.receipt.request.clone(),
            next: None,
        }
    }

    fn forward_final_settlement(
        &mut self,
        receipt: AddLiquidityTransferReceipt,
    ) -> Option<HandlerOutcome<PoolMessage, PoolResponse>> {
        let mut outcome = HandlerOutcome::new();
        outcome.with_message(
            self.runtime.borrow_mut().application_creator_chain_id(),
            PoolMessage::AddLiquidityTransferReceipt { receipt },
            false,
        );

        Some(outcome)
    }

    async fn exec_successor(
        &mut self,
    ) -> Result<Option<HandlerOutcome<PoolMessage, PoolResponse>>, HandlerError> {
        if let Some(next) = self.receipt.next.clone() {
            if next.token.is_some() {
                let mut handler = RequestMemeFundExtHandler::new(
                    self.runtime.clone(),
                    self.state.clone(),
                    Some(self.receipt.request.clone()),
                    next,
                    None,
                );
                return handler.handle().await;
            }

            self.transfer_native(next.amount_in).await;
            return Ok(self.forward_final_settlement(self.final_settlement_receipt()));
        }

        Ok(self.forward_final_settlement(self.receipt.clone()))
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
        self.exec_successor().await
    }
}
