use crate::interfaces::state::StateInterface;
use abi::swap::pool::{PoolMessage, PoolOperation, PoolResponse};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::{Account, Amount, Timestamp};
use runtime::interfaces::{access_control::AccessControl, contract::ContractRuntimeContext};
use std::{cell::RefCell, rc::Rc};

pub struct RemoveLiquidityHandler<R: ContractRuntimeContext + AccessControl, S: StateInterface> {
    runtime: Rc<RefCell<R>>,
    _state: S,

    liquidity: Amount,
    amount_0_out_min: Option<Amount>,
    amount_1_out_min: Option<Amount>,
    to: Option<Account>,
    block_timestamp: Option<Timestamp>,
}

impl<R: ContractRuntimeContext + AccessControl, S: StateInterface> RemoveLiquidityHandler<R, S> {
    pub fn new(runtime: Rc<RefCell<R>>, state: S, op: &PoolOperation) -> Self {
        let PoolOperation::RemoveLiquidity {
            liquidity,
            amount_0_out_min,
            amount_1_out_min,
            to,
            block_timestamp,
        } = op
        else {
            panic!("Invalid operation");
        };

        Self {
            _state: state,
            runtime,

            liquidity: *liquidity,
            amount_0_out_min: *amount_0_out_min,
            amount_1_out_min: *amount_1_out_min,
            to: *to,
            block_timestamp: *block_timestamp,
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl, S: StateInterface>
    Handler<PoolMessage, PoolResponse> for RemoveLiquidityHandler<R, S>
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<PoolMessage, PoolResponse>>, HandlerError> {
        assert!(self.liquidity > Amount::ZERO, "Invalid amount");

        let origin = self.runtime.borrow_mut().authenticated_account();

        let destination = self.runtime.borrow_mut().application_creator_chain_id();
        let mut outcome = HandlerOutcome::new();

        outcome.with_message(
            destination,
            PoolMessage::RemoveLiquidity {
                origin,
                liquidity: self.liquidity,
                amount_0_out_min: self.amount_0_out_min,
                amount_1_out_min: self.amount_1_out_min,
                to: self.to,
                block_timestamp: self.block_timestamp,
            },
        );

        Ok(Some(outcome))
    }
}
