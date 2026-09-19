use crate::interfaces::{parameters::ParametersInterface, state::StateInterface};
use abi::pool::{PoolMessage, PoolResponse, Transaction, TransactionType};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::{Account, Amount, ApplicationId, Timestamp};
use runtime::interfaces::{
    access_control::AccessControl, contract::ContractRuntimeContext, meme::MemeRuntimeContext,
};
use std::{cell::RefCell, rc::Rc};

pub struct RemoveLiquidityHandler<
    R: ContractRuntimeContext + AccessControl + ParametersInterface + MemeRuntimeContext,
    S: StateInterface,
> {
    runtime: Rc<RefCell<R>>,
    state: S,

    origin: Account,
    liquidity: Amount,
    amount_0_out_min: Option<Amount>,
    amount_1_out_min: Option<Amount>,
    to: Option<Account>,
    block_timestamp: Option<Timestamp>,
}

impl<
        R: ContractRuntimeContext + AccessControl + ParametersInterface + MemeRuntimeContext,
        S: StateInterface,
    > RemoveLiquidityHandler<R, S>
{
    pub fn new(runtime: Rc<RefCell<R>>, state: S, msg: &PoolMessage) -> Self {
        let PoolMessage::RemoveLiquidity {
            origin,
            liquidity,
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
            liquidity: *liquidity,
            amount_0_out_min: *amount_0_out_min,
            amount_1_out_min: *amount_1_out_min,
            to: *to,
            block_timestamp: *block_timestamp,
        }
    }

    async fn credit(
        &mut self,
        token: Option<ApplicationId>,
        owner: Account,
        amount: Amount,
    ) -> Result<(), HandlerError> {
        if amount == Amount::ZERO {
            return Ok(());
        }

        self.state
            .credit_claimable(token, owner, amount)
            .await
            .map_err(|error| HandlerError::ProcessError(error.into()))
    }
}

#[async_trait(?Send)]
impl<
        R: ContractRuntimeContext + AccessControl + ParametersInterface + MemeRuntimeContext,
        S: StateInterface,
    > Handler<PoolMessage, PoolResponse> for RemoveLiquidityHandler<R, S>
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<PoolMessage, PoolResponse>>, HandlerError> {
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

        assert!(
            pool.reserve_0 > Amount::ZERO
                && pool.reserve_1 > Amount::ZERO
                && total_supply > Amount::ZERO,
            "Pool is not ready"
        );

        let timestamp = self
            .block_timestamp
            .unwrap_or(self.runtime.borrow_mut().system_time());

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

        let (amount_0, amount_1) = pool
            .try_calculate_liquidity_amount_pair(
                self.liquidity,
                total_supply,
                self.amount_0_out_min,
                self.amount_1_out_min,
            )
            .map_err(|error| HandlerError::ProcessError(Box::new(error)))?;

        self.state
            .burn_shares(self.origin, self.liquidity)
            .await
            .map_err(|error| HandlerError::ProcessError(error.into()))?;

        let reserve_0 = pool
            .reserve_0
            .try_sub(amount_0)
            .map_err(|error| HandlerError::ProcessError(Box::new(error)))?;
        let reserve_1 = pool
            .reserve_1
            .try_sub(amount_1)
            .map_err(|error| HandlerError::ProcessError(Box::new(error)))?;
        pool.liquid(reserve_0, reserve_1, timestamp);
        pool.update_k_last();
        self.state
            .set_pool(pool)
            .await
            .map_err(|error| HandlerError::ProcessError(error.into()))?;

        let to = self.to.unwrap_or(self.origin);
        let token_0 = self.runtime.borrow_mut().token_0();
        let token_1 = self.runtime.borrow_mut().token_1();
        self.credit(Some(token_0), to, amount_0).await?;
        self.credit(token_1, to, amount_1).await?;

        let transaction = self
            .state
            .build_transaction(Transaction {
                transaction_id: None,
                transaction_type: TransactionType::RemoveLiquidity,
                from: self.origin,
                amount_0_in: None,
                amount_1_in: None,
                amount_0_out: Some(amount_0),
                amount_1_out: Some(amount_1),
                liquidity: Some(self.liquidity),
                created_at: timestamp,
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
