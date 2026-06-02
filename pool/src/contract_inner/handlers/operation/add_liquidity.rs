use crate::{
    contract_inner::handlers::request_meme_fund_ext::RequestMemeFundExtHandler,
    interfaces::{parameters::ParametersInterface, state::StateInterface},
};
use abi::swap::pool::{FundRequestExt, FundType, PoolMessage, PoolOperation, PoolResponse};
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
    > Handler<PoolMessage, PoolResponse> for AddLiquidityHandler<R, S>
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<PoolMessage, PoolResponse>>, HandlerError> {
        assert!(
            self.amount_0_in > Amount::ZERO && self.amount_1_in > Amount::ZERO,
            "Invalid amount"
        );

        let origin = self.runtime.borrow_mut().authenticated_account();
        let token_0 = self.runtime.borrow_mut().token_0();
        let token_1 = self.runtime.borrow_mut().token_1();

        let fund_request_0 = FundRequestExt::builder(
            origin,
            Some(token_0),
            self.amount_0_in,
            FundType::AddLiquidity,
        )
        .amount_out_min(self.amount_0_out_min)
        .counterparty_token(token_1)
        .counterparty_amount_in(Some(self.amount_1_in))
        .counterparty_amount_out_min(self.amount_1_out_min)
        .to(self.to)
        .block_timestamp(self.block_timestamp)
        .build();

        let fund_request_1 =
            FundRequestExt::builder(origin, token_1, self.amount_1_in, FundType::AddLiquidity)
                .amount_out_min(self.amount_1_out_min)
                .counterparty_token(Some(token_0))
                .counterparty_amount_in(Some(self.amount_0_in))
                .counterparty_amount_out_min(self.amount_0_out_min)
                .to(self.to)
                .block_timestamp(self.block_timestamp)
                .build();

        let mut handler = RequestMemeFundExtHandler::new(
            self.runtime.clone(),
            self.state.clone(),
            None,
            fund_request_0,
            Some(fund_request_1),
        );
        handler.handle().await
    }
}
