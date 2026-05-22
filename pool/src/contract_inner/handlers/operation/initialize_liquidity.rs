use crate::interfaces::{parameters::ParametersInterface, state::StateInterface};
use abi::swap::pool::{BootstrapPolicy, PoolMessage, PoolOperation, PoolResponse};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::{Account, Amount, Timestamp};
use runtime::interfaces::{
    access_control::AccessControl, contract::ContractRuntimeContext, meme::MemeRuntimeContext,
};
use std::{cell::RefCell, marker::PhantomData, rc::Rc};

pub struct InitializeLiquidityHandler<
    R: ContractRuntimeContext + AccessControl + MemeRuntimeContext + ParametersInterface,
    S: StateInterface,
> {
    runtime: Rc<RefCell<R>>,
    amount_0_in: Amount,
    amount_1_in: Amount,
    to: Option<Account>,
    block_timestamp: Option<Timestamp>,
    _state: PhantomData<S>,
}

impl<
        R: ContractRuntimeContext + AccessControl + MemeRuntimeContext + ParametersInterface,
        S: StateInterface,
    > InitializeLiquidityHandler<R, S>
{
    pub fn new(runtime: Rc<RefCell<R>>, _state: S, op: &PoolOperation) -> Self {
        let PoolOperation::InitializeLiquidity {
            amount_0_in,
            amount_1_in,
            to,
            block_timestamp,
        } = op
        else {
            panic!("Invalid operation");
        };

        Self {
            runtime,

            amount_0_in: *amount_0_in,
            amount_1_in: *amount_1_in,
            to: *to,
            block_timestamp: *block_timestamp,
            _state: PhantomData,
        }
    }
}

#[async_trait(?Send)]
impl<
        R: ContractRuntimeContext + AccessControl + MemeRuntimeContext + ParametersInterface,
        S: StateInterface,
    > Handler<PoolMessage, PoolResponse> for InitializeLiquidityHandler<R, S>
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<PoolMessage, PoolResponse>>, HandlerError> {
        assert!(
            self.amount_0_in > Amount::ZERO && self.amount_1_in > Amount::ZERO,
            "Invalid amount"
        );

        let token_0 = self.runtime.borrow_mut().token_0();
        let BootstrapPolicy::MemeInitializeLiquidity {
            virtual_initial_liquidity: _,
        } = self.runtime.borrow_mut().bootstrap_policy()
        else {
            panic!("InitializeLiquidity operation is only valid for meme initialization");
        };
        assert!(
            self.runtime.borrow_mut().token_1().is_none(),
            "Invalid initialization pair"
        );
        assert!(
            self.runtime
                .borrow_mut()
                .authenticated_caller_id()
                .expect("Invalid initialization caller")
                == token_0,
            "Invalid initialization caller"
        );
        let destination = self.runtime.borrow_mut().application_creator_chain_id();
        let origin = self.runtime.borrow_mut().creator();
        let mut outcome = HandlerOutcome::new();
        outcome.with_message(
            destination,
            PoolMessage::InitializeLiquidity {
                origin,
                amount_0_in: self.amount_0_in,
                amount_1_in: self.amount_1_in,
                to: self.to,
                block_timestamp: self.block_timestamp,
            },
        );

        Ok(Some(outcome))
    }
}
