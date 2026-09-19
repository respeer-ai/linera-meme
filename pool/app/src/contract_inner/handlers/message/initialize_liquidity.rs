use crate::interfaces::{parameters::ParametersInterface, state::StateInterface};
use abi::pool::{BootstrapPolicy, PoolMessage, PoolResponse, Transaction, TransactionType};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::{Account, Amount, Timestamp};
use runtime::interfaces::{access_control::AccessControl, contract::ContractRuntimeContext};
use std::{cell::RefCell, rc::Rc};

pub struct InitializeLiquidityHandler<
    R: ContractRuntimeContext + AccessControl + ParametersInterface,
    S: StateInterface,
> {
    runtime: Rc<RefCell<R>>,
    state: S,
    origin: Account,
    amount_0_in: Amount,
    amount_1_in: Amount,
    to: Option<Account>,
    block_timestamp: Option<Timestamp>,
}

impl<R: ContractRuntimeContext + AccessControl + ParametersInterface, S: StateInterface>
    InitializeLiquidityHandler<R, S>
{
    pub fn new(runtime: Rc<RefCell<R>>, state: S, msg: &PoolMessage) -> Self {
        let PoolMessage::InitializeLiquidity {
            origin,
            amount_0_in,
            amount_1_in,
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
            to: *to,
            block_timestamp: *block_timestamp,
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl + ParametersInterface, S: StateInterface>
    Handler<PoolMessage, PoolResponse> for InitializeLiquidityHandler<R, S>
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<PoolMessage, PoolResponse>>, HandlerError> {
        let BootstrapPolicy::MemeInitializeLiquidity {
            virtual_initial_liquidity: _,
        } = self.runtime.borrow_mut().bootstrap_policy()
        else {
            panic!("InitializeLiquidity message is only valid for meme initialization");
        };

        let to = self.to.unwrap_or(self.origin);
        let timestamp = self
            .block_timestamp
            .unwrap_or(self.runtime.borrow_mut().system_time());

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

        // Guards previously enforced inside state: pool must not be
        // initialized yet, and both amounts must be positive.
        assert!(
            !(pool.reserve_0 > Amount::ZERO
                && pool.reserve_1 > Amount::ZERO
                && total_supply > Amount::ZERO),
            "Pool already initialized"
        );
        assert!(self.amount_0_in > Amount::ZERO, "Invalid amount");
        assert!(self.amount_1_in > Amount::ZERO, "Invalid amount");

        // Business math (mint_fee / calculate_liquidity / liquid) stays here;
        // state only records shares and the updated pool record.
        let fee_share = pool.mint_fee(total_supply);
        self.state
            .mint_shares(pool.fee_to, fee_share)
            .await
            .map_err(|error| HandlerError::ProcessError(error.into()))?;
        let liquidity = pool.calculate_liquidity(total_supply, self.amount_0_in, self.amount_1_in);
        self.state
            .mint_shares(to, liquidity)
            .await
            .map_err(|error| HandlerError::ProcessError(error.into()))?;

        pool.liquid(self.amount_0_in, self.amount_1_in, timestamp);
        pool.update_k_last();
        self.state
            .set_pool(pool)
            .await
            .map_err(|error| HandlerError::ProcessError(error.into()))?;

        let transaction = self
            .state
            .build_transaction(Transaction {
                transaction_id: None,
                transaction_type: TransactionType::AddLiquidity,
                from: self.origin,
                amount_0_in: Some(self.amount_0_in),
                amount_1_in: Some(self.amount_1_in),
                amount_0_out: None,
                amount_1_out: None,
                liquidity: Some(liquidity),
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
