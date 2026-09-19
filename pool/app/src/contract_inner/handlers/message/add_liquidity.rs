use crate::interfaces::{parameters::ParametersInterface, state::StateInterface};
use abi::pool::{PoolMessage, PoolResponse, Transaction, TransactionType};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::{Account, Amount, ApplicationId, Timestamp};
use runtime::interfaces::{
    access_control::AccessControl, contract::ContractRuntimeContext, meme::MemeRuntimeContext,
};
use std::{cell::RefCell, rc::Rc};

pub struct AddLiquidityHandler<
    R: ContractRuntimeContext + AccessControl + ParametersInterface + MemeRuntimeContext,
    S: StateInterface,
> {
    runtime: Rc<RefCell<R>>,
    state: S,

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
            runtime,
            state,

            origin: *origin,
            amount_0_in: *amount_0_in,
            amount_1_in: *amount_1_in,
            amount_0_out_min: *amount_0_out_min,
            amount_1_out_min: *amount_1_out_min,
            to: *to,
            block_timestamp: *block_timestamp,
        }
    }

    async fn credit(
        &mut self,
        token: Option<ApplicationId>,
        amount: Amount,
    ) -> Result<(), HandlerError> {
        if amount == Amount::ZERO {
            return Ok(());
        }

        self.state
            .credit_claimable(token, self.origin, amount)
            .await
            .map_err(|error| HandlerError::ProcessError(error.into()))
    }

    async fn credit_amount_pair(
        &mut self,
        amount_0: Amount,
        amount_1: Amount,
    ) -> Result<(), HandlerError> {
        let token_0 = self.runtime.borrow_mut().token_0();
        let token_1 = self.runtime.borrow_mut().token_1();
        self.credit(Some(token_0), amount_0).await?;
        self.credit(token_1, amount_1).await
    }

    async fn calculate_amount_pair(&mut self) -> Result<Option<(Amount, Amount)>, HandlerError> {
        let pool = self
            .state
            .pool()
            .await
            .map_err(|error| HandlerError::ProcessError(error.into()))?;
        let amount_pair_result = pool.try_calculate_swap_amount_pair(
            self.amount_0_in,
            self.amount_1_in,
            self.amount_0_out_min,
            self.amount_1_out_min,
        );

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
            self.credit(Some(token_0), self.amount_0_in.try_sub(amount_0)?)
                .await?;
        }
        if self.amount_1_in > amount_1 {
            let token_1 = self.runtime.borrow_mut().token_1();
            self.credit(token_1, self.amount_1_in.try_sub(amount_1)?)
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
        let block_timestamp = self.block_timestamp.unwrap_or(timestamp);

        let liquidity_result: Result<Amount, HandlerError> = async {
            let mut pool = self
                .state
                .pool()
                .await
                .map_err(|error| HandlerError::ProcessError(error.into()))?;
            let total_supply = self
                .state
                .total_supply()
                .await
                .map_err(|error| HandlerError::ProcessError(error.into()))?;
            let reserve_0 = pool
                .reserve_0
                .try_add(amount_0)
                .map_err(|error| HandlerError::ProcessError(Box::new(error)))?;
            let reserve_1 = pool
                .reserve_1
                .try_add(amount_1)
                .map_err(|error| HandlerError::ProcessError(Box::new(error)))?;

            let fee_share = pool.mint_fee(total_supply);
            self.state
                .mint_shares(pool.fee_to, fee_share)
                .await
                .map_err(|error| HandlerError::ProcessError(error.into()))?;
            // Re-read the total supply after minting the fee share, mirroring
            // the original implementation where the fee mint happened first.
            let total_supply = self
                .state
                .total_supply()
                .await
                .map_err(|error| HandlerError::ProcessError(error.into()))?;
            let liquidity = pool.calculate_liquidity(total_supply, amount_0, amount_1);
            self.state
                .mint_shares(to, liquidity)
                .await
                .map_err(|error| HandlerError::ProcessError(error.into()))?;

            pool.liquid(reserve_0, reserve_1, block_timestamp);
            pool.update_k_last();
            self.state
                .set_pool(pool)
                .await
                .map_err(|error| HandlerError::ProcessError(error.into()))?;

            Ok(liquidity)
        }
        .await;

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

        let transaction = self
            .state
            .build_transaction(Transaction {
                transaction_id: None,
                transaction_type: TransactionType::AddLiquidity,
                from: self.origin,
                amount_0_in: Some(amount_0),
                amount_1_in: Some(amount_1),
                amount_0_out: None,
                amount_1_out: None,
                liquidity: Some(liquidity),
                created_at: block_timestamp,
            })
            .await
            .map_err(|error| HandlerError::ProcessError(error.into()))?;

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
