use crate::{
    contract_inner::handlers::request_meme_fund::RequestMemeFundHandler,
    interfaces::{parameters::ParametersInterface, state::StateInterface},
    FundRequest, FundStatus, FundType,
};
use abi::swap::pool::{PoolMessage, PoolOperation};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::{Account, Amount, Timestamp};
use runtime::interfaces::{
    access_control::AccessControl, contract::ContractRuntimeContext, meme::MemeRuntimeContext,
};
use std::{cell::RefCell, rc::Rc};

pub struct AddLiquidityHandler<
    R: ContractRuntimeContext + AccessControl + MemeRuntimeContext + ParametersInterface,
    S: StateInterface,
> {
    runtime: Rc<RefCell<R>>,
    state: Rc<RefCell<S>>,

    amount_0_in: Amount,
    amount_1_in: Amount,
    amount_0_out_min: Option<Amount>,
    amount_1_out_min: Option<Amount>,
    to: Option<Account>,
    block_timestamp: Option<Timestamp>,
}

impl<
        R: ContractRuntimeContext + AccessControl + MemeRuntimeContext + ParametersInterface,
        S: StateInterface,
    > AddLiquidityHandler<R, S>
{
    pub fn new(runtime: Rc<RefCell<R>>, state: S, op: &PoolOperation) -> Self {
        let PoolOperation::AddLiquidity {
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
}

#[async_trait(?Send)]
impl<
        R: ContractRuntimeContext + AccessControl + MemeRuntimeContext + ParametersInterface,
        S: StateInterface,
    > Handler<PoolMessage> for AddLiquidityHandler<R, S>
{
    async fn handle(&mut self) -> Result<Option<HandlerOutcome<PoolMessage>>, HandlerError> {
        assert!(
            self.amount_0_in > Amount::ZERO && self.amount_1_in > Amount::ZERO,
            "Invalid amount"
        );

        let origin = self.runtime.borrow_mut().authenticated_account();

        // 1: Transfer funds of token_0
        let mut fund_request_0 = FundRequest {
            from: origin,
            token: Some(self.runtime.borrow_mut().token_0()),
            amount_in: self.amount_0_in,
            pair_token_amount_out_min: self.amount_1_out_min,
            to: self.to,
            block_timestamp: self.block_timestamp,
            fund_type: FundType::AddLiquidity,
            status: FundStatus::InFlight,
            error: None,
            prev_request: None,
            next_request: None,
        };
        let transfer_id_0 = self
            .state
            .borrow_mut()
            .create_fund_request(fund_request_0.clone())
            .map_err(Into::into)?;

        let fund_request_1 = FundRequest {
            from: origin,
            token: self.runtime.borrow_mut().token_1(),
            amount_in: self.amount_1_in,
            pair_token_amount_out_min: self.amount_0_out_min,
            to: self.to,
            block_timestamp: self.block_timestamp,
            fund_type: FundType::AddLiquidity,
            status: FundStatus::Created,
            error: None,
            prev_request: Some(transfer_id_0),
            next_request: None,
        };
        let transfer_id_1 = self
            .state
            .borrow_mut()
            .create_fund_request(fund_request_1)
            .map_err(Into::into)?;

        fund_request_0.next_request = Some(transfer_id_1);
        self.state
            .borrow_mut()
            .update_fund_request(transfer_id_0, fund_request_0)
            .await
            .map_err(Into::into)?;

        let mut handler = RequestMemeFundHandler::new(
            self.runtime.clone(),
            self.state.clone(),
            self.runtime.borrow_mut().token_0(),
            self.amount_0_in,
            transfer_id_0,
        );
        handler.handle().await
    }
}
