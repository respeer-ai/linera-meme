use crate::{
    contract_inner::handlers::{
        fund_pool_application_creation_chain::FundPoolApplicationCreationChainHandler,
        request_meme_fund::RequestMemeFundHandler,
    },
    interfaces::{parameters::ParametersInterface, state::StateInterface},
    FundRequest, FundStatus, FundType,
};
use abi::swap::pool::{PoolMessage, PoolOperation, PoolResponse};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::{Account, Amount, Timestamp};
use runtime::interfaces::{
    access_control::AccessControl, contract::ContractRuntimeContext, meme::MemeRuntimeContext,
};
use std::{cell::RefCell, rc::Rc};

pub struct SwapHandler<
    R: ContractRuntimeContext + AccessControl + MemeRuntimeContext + ParametersInterface,
    S: StateInterface,
> {
    runtime: Rc<RefCell<R>>,
    state: Rc<RefCell<S>>,

    amount_0_in: Option<Amount>,
    amount_1_in: Option<Amount>,
    amount_0_out_min: Option<Amount>,
    amount_1_out_min: Option<Amount>,
    to: Option<Account>,
    block_timestamp: Option<Timestamp>,
}

impl<
        R: ContractRuntimeContext + AccessControl + MemeRuntimeContext + ParametersInterface,
        S: StateInterface,
    > SwapHandler<R, S>
{
    pub fn new(runtime: Rc<RefCell<R>>, state: S, op: &PoolOperation) -> Self {
        let PoolOperation::Swap {
            amount_0_in,
            amount_1_in,
            amount_0_out_min,
            amount_1_out_min,
            to,
            block_timestamp,
        } = op
        else {
            panic!("Invalid operation");
        };

        Self {
            state: Rc::new(RefCell::new(state)),
            runtime,

            amount_0_in: *amount_0_in,
            amount_1_in: *amount_1_in,
            amount_0_out_min: *amount_0_out_min,
            amount_1_out_min: *amount_1_out_min,
            to: *to,
            block_timestamp: *block_timestamp,
        }
    }

    async fn fund_pool_application_creation_chain(&mut self, amount: Amount) {
        let _ = FundPoolApplicationCreationChainHandler::new(
            self.runtime.clone(),
            self.state.clone(),
            amount,
        )
        .handle()
        .await;
    }
}

#[async_trait(?Send)]
impl<
        R: ContractRuntimeContext + AccessControl + MemeRuntimeContext + ParametersInterface,
        S: StateInterface,
    > Handler<PoolMessage, PoolResponse> for SwapHandler<R, S>
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<PoolMessage, PoolResponse>>, HandlerError> {
        assert!(
            !(self.amount_0_in.is_some() && self.amount_1_in.is_some())
                && (self.amount_0_in.is_some() || self.amount_1_in.is_some()),
            "Invalid amount"
        );

        let origin = self.runtime.borrow_mut().authenticated_account();
        let token_0 = self.runtime.borrow_mut().token_0();

        log::info!(
            "Swapping token_0 {} origin {} amount 0 {:?} amount 1 {:?}",
            token_0,
            origin,
            self.amount_0_in,
            self.amount_1_in,
        );

        if let Some(amount_0_in) = self.amount_0_in {
            assert!(amount_0_in > Amount::ZERO, "Invalid amount");

            let fund_request = FundRequest {
                from: origin,
                token: Some(token_0),
                amount_in: amount_0_in,
                pair_token_amount_out_min: self.amount_1_out_min,
                to: self.to,
                block_timestamp: self.block_timestamp,
                fund_type: FundType::Swap,
                status: FundStatus::InFlight,
                error: None,
                prev_request: None,
                next_request: None,
            };

            let transfer_id = match self.state.borrow_mut().create_fund_request(fund_request) {
                Ok(id) => id,
                Err(err) => return Err(HandlerError::ProcessError(Box::new(err))),
            };

            let mut handler = RequestMemeFundHandler::new(
                self.runtime.clone(),
                self.state.clone(),
                token_0,
                amount_0_in,
                transfer_id,
            );
            return handler.handle().await;
        }

        let Some(amount) = self.amount_1_in else {
            panic!("Invalid amount");
        };
        assert!(amount > Amount::ZERO, "Invalid amount");

        let token_1 = self.runtime.borrow_mut().token_1();

        if let Some(token_1) = token_1 {
            let fund_request = FundRequest {
                from: origin,
                token: Some(token_1),
                amount_in: amount,
                pair_token_amount_out_min: self.amount_0_out_min,
                to: self.to,
                block_timestamp: self.block_timestamp,
                fund_type: FundType::Swap,
                status: FundStatus::InFlight,
                error: None,
                prev_request: None,
                next_request: None,
            };

            let transfer_id = match self.state.borrow_mut().create_fund_request(fund_request) {
                Ok(id) => id,
                Err(err) => return Err(HandlerError::ProcessError(Box::new(err))),
            };

            let mut handler = RequestMemeFundHandler::new(
                self.runtime.clone(),
                self.state.clone(),
                token_1,
                amount,
                transfer_id,
            );
            return handler.handle().await;
        }

        self.fund_pool_application_creation_chain(amount).await;

        let destination = self.runtime.borrow_mut().application_creator_chain_id();
        let mut outcome = HandlerOutcome::new();

        outcome.with_message(
            destination,
            PoolMessage::Swap {
                origin,
                amount_0_in: self.amount_0_in,
                amount_1_in: self.amount_1_in,
                amount_0_out_min: self.amount_0_out_min,
                amount_1_out_min: self.amount_1_out_min,
                to: self.to,
                block_timestamp: self.block_timestamp,
            },
        );

        Ok(Some(outcome))
    }
}
