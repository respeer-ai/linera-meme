use crate::interfaces::{parameters::ParametersInterface, state::StateInterface};
use abi::{
    meme_token::MemeToken,
    swap::pool::{PoolMessage, PoolResponse},
};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::{Account, Amount, Timestamp};
use runtime::interfaces::{
    access_control::AccessControl, contract::ContractRuntimeContext, meme::MemeRuntimeContext,
};
use std::{cell::RefCell, rc::Rc};

pub struct AddLiquidityHandler<
    R: ContractRuntimeContext + AccessControl + ParametersInterface + MemeRuntimeContext,
    S: StateInterface,
> {
    runtime: Rc<RefCell<R>>,
    state: Rc<RefCell<S>>,

    origin: Account,
    amount_0_in: Amount,
    amount_1_in: Amount,
    amount_0_out_min: Option<Amount>,
    amount_1_out_min: Option<Amount>,
    to: Option<Account>,
    block_timestamp: Option<Timestamp>,
}

impl<
        R: ContractRuntimeContext + AccessControl + ParametersInterface + MemeRuntimeContext,
        S: StateInterface,
    > AddLiquidityHandler<R, S>
{
    pub fn new(runtime: Rc<RefCell<R>>, state: S, msg: &PoolMessage) -> Self {
        let PoolMessage::AddLiquidity {
            origin,
            amount_0_in,
            amount_1_in,
            amount_0_out_min,
            amount_1_out_min,
            to,
            block_timestamp,
        } = msg
        else {
            panic!("Invalid message");
        };

        Self {
            state: Rc::new(RefCell::new(state)),
            runtime,

            origin: *origin,
            amount_0_in: *amount_0_in,
            amount_1_in: *amount_1_in,
            amount_0_out_min: *amount_0_out_min,
            amount_1_out_min: *amount_1_out_min,
            to: *to,
            block_timestamp: *block_timestamp,
        }
    }

    async fn credit(&mut self, token: MemeToken, amount: Amount) -> Result<(), HandlerError> {
        if amount == Amount::ZERO {
            return Ok(());
        }

        self.state
            .borrow_mut()
            .credit(token, self.origin, amount)
            .await
            .map_err(Into::into)
    }

    async fn credit_amount_pair(
        &mut self,
        amount_0: Amount,
        amount_1: Amount,
    ) -> Result<(), HandlerError> {
        let token_0 = self.runtime.borrow_mut().token_0();
        let token_1 = self.runtime.borrow_mut().token_1();
        self.credit(MemeToken::from(token_0), amount_0).await?;
        self.credit(MemeToken::from(token_1), amount_1).await
    }

    async fn calculate_amount_pair(&mut self) -> Result<Option<(Amount, Amount)>, HandlerError> {
        let amount_pair_result = {
            self.state.borrow().try_calculate_swap_amount_pair(
                self.amount_0_in,
                self.amount_1_in,
                self.amount_0_out_min,
                self.amount_1_out_min,
            )
        };

        let (amount_0, amount_1) = match amount_pair_result {
            Ok(amounts) => amounts,
            Err(_) => {
                self.credit_amount_pair(self.amount_0_in, self.amount_1_in)
                    .await?;
                return Ok(None);
            }
        };

        if amount_0 == Amount::ZERO || amount_1 == Amount::ZERO {
            self.credit_amount_pair(self.amount_0_in, self.amount_1_in)
                .await?;
            return Ok(None);
        }

        Ok(Some((amount_0, amount_1)))
    }

    async fn credit_excess(
        &mut self,
        amount_0: Amount,
        amount_1: Amount,
    ) -> Result<(), HandlerError> {
        if self.amount_0_in > amount_0 {
            let token_0 = self.runtime.borrow_mut().token_0();
            self.credit(
                MemeToken::from(token_0),
                self.amount_0_in.try_sub(amount_0)?,
            )
            .await?;
        }
        if self.amount_1_in > amount_1 {
            let token_1 = self.runtime.borrow_mut().token_1();
            self.credit(
                MemeToken::from(token_1),
                self.amount_1_in.try_sub(amount_1)?,
            )
            .await?;
        }
        Ok(())
    }
}

#[async_trait(?Send)]
impl<
        R: ContractRuntimeContext + AccessControl + ParametersInterface + MemeRuntimeContext,
        S: StateInterface,
    > Handler<PoolMessage, PoolResponse> for AddLiquidityHandler<R, S>
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<PoolMessage, PoolResponse>>, HandlerError> {
        // We already receive all funds here
        let Some((amount_0, amount_1)) = self.calculate_amount_pair().await? else {
            return Ok(None);
        };

        let to = self.to.unwrap_or(self.origin);
        let timestamp = self.runtime.borrow_mut().system_time();
        let liquidity_result = {
            self.state
                .borrow_mut()
                .add_liquidity(
                    amount_0,
                    amount_1,
                    to,
                    self.block_timestamp.unwrap_or(timestamp),
                )
                .await
        };
        let liquidity = match liquidity_result {
            Ok(liquidity) => liquidity,
            Err(err) => {
                self.credit_amount_pair(self.amount_0_in, self.amount_1_in)
                    .await?;
                log::warn!("Failed add liquidity after custody: {}", err);
                return Ok(None);
            }
        };

        self.credit_excess(amount_0, amount_1).await?;

        let transaction = self.state.borrow_mut().build_transaction(
            self.origin,
            Some(amount_0),
            Some(amount_1),
            None,
            None,
            Some(liquidity),
            self.block_timestamp.unwrap_or(timestamp),
        );

        let destination = self.runtime.borrow_mut().chain_id();
        let mut outcome = HandlerOutcome::new();

        outcome.with_message(
            destination,
            PoolMessage::NewTransaction { transaction },
            false,
        );

        Ok(Some(outcome))
    }
}
