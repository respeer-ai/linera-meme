use crate::{
    contract_inner::handlers::create_pool::CreatePoolHandler, interfaces::state::StateInterface,
};
use abi::swap::{Metadata, SwapMessage};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use runtime::interfaces::{access_control::AccessControl, contract::ContractRuntimeContext};
use std::{cell::RefCell, rc::Rc};

pub struct InitializeLiquidityHandler<R: ContractRuntimeContext + AccessControl, S: StateInterface>
{
    runtime: Rc<RefCell<R>>,
    state: S,

    creator: Account,
    token_0: ApplicationId,
    amount_0: Amount,
    amount_1: Amount,
    // Only for creator to initialize pool
    virtual_liquidity: bool,
    to: Option<Account>,
}

impl<R: ContractRuntimeContext + AccessControl, S: StateInterface>
    InitializeLiquidityHandler<R, S>
{
    pub fn new(runtime: Rc<RefCell<R>>, state: S, msg: &SwapMessage) -> Self {
        let SwapMessage::InitializeLiquidity {
            creator,
            token_0,
            amount_0,
            amount_1,
            virtual_liquidity,
            to,
        } = msg
        else {
            panic!("Invalid message");
        };

        Self {
            state,
            runtime,

            creator: *creator,
            token_0: *token_0,
            amount_0: *amount_0,
            amount_1: *amount_1,
            virtual_liquidity: *virtual_liquidity,
            to: *to,
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl, S: StateInterface> Handler<SwapMessage>
    for InitializeLiquidityHandler<R, S>
{
    async fn handle(&mut self) -> Result<Option<HandlerOutcome<SwapMessage>>, HandlerError> {
        let handler = CreatePoolHandler::new(
            self.runtime,
            self.state,
            creator,
            token_0,
            None,
            amount_0,
            amount_1,
            virtual_liquidity,
            to,
            None,
            false,
        );

        handler.handle()
    }
}
