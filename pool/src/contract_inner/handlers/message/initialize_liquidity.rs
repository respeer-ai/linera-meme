use crate::interfaces::{parameters::ParametersInterface, state::StateInterface};
use abi::swap::pool::{BootstrapPolicy, PoolMessage, PoolResponse};
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
    state: Rc<RefCell<S>>,
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
            state: Rc::new(RefCell::new(state)),
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

        let liquidity = self
            .state
            .borrow_mut()
            .initialize_liquidity(self.amount_0_in, self.amount_1_in, to, timestamp)
            .await
            .map_err(Into::into)?;

        let transaction = self.state.borrow_mut().build_transaction(
            self.origin,
            Some(self.amount_0_in),
            Some(self.amount_1_in),
            None,
            None,
            Some(liquidity),
            timestamp,
        );

        let destination = self.runtime.borrow_mut().chain_id();
        let mut outcome = HandlerOutcome::new();
        outcome.with_message(destination, PoolMessage::NewTransaction { transaction });
        Ok(Some(outcome))
    }
}
