use crate::{
    contract_inner::handlers::create_pool::CreatePoolHandler, interfaces::state::StateInterface,
};
use abi::swap::router::SwapMessage;
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::{Account, Amount, ApplicationId, ChainId};
use runtime::interfaces::{
    access_control::AccessControl, contract::ContractRuntimeContext, meme::MemeRuntimeContext,
};
use std::{cell::RefCell, rc::Rc};

pub struct InitializeLiquidityHandler<
    R: ContractRuntimeContext + AccessControl + MemeRuntimeContext,
    S: StateInterface,
> {
    runtime: Rc<RefCell<R>>,
    state: Rc<RefCell<S>>,

    creator: Account,
    token_0_creator_chain_id: ChainId,
    token_0: ApplicationId,
    amount_0: Amount,
    amount_1: Amount,
    // Only for creator to initialize pool
    virtual_liquidity: bool,
    to: Option<Account>,
}

impl<R: ContractRuntimeContext + AccessControl + MemeRuntimeContext, S: StateInterface>
    InitializeLiquidityHandler<R, S>
{
    pub fn new(runtime: Rc<RefCell<R>>, state: S, msg: &SwapMessage) -> Self {
        let SwapMessage::InitializeLiquidity {
            creator,
            token_0_creator_chain_id,
            token_0,
            amount_0,
            amount_1,
            virtual_liquidity,
            to,
        } = msg
        else {
            panic!("Invalid message");
        };

        // It's not safe here to get creator chain id from meme application so we have to pass and record it

        Self {
            state: Rc::new(RefCell::new(state)),
            runtime,

            creator: *creator,
            token_0_creator_chain_id: *token_0_creator_chain_id,
            token_0: *token_0,
            amount_0: *amount_0,
            amount_1: *amount_1,
            virtual_liquidity: *virtual_liquidity,
            to: *to,
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl + MemeRuntimeContext, S: StateInterface>
    Handler<SwapMessage> for InitializeLiquidityHandler<R, S>
{
    async fn handle(&mut self) -> Result<Option<HandlerOutcome<SwapMessage>>, HandlerError> {
        let mut handler = CreatePoolHandler::new(
            self.runtime.clone(),
            self.state.clone(),
            self.creator,
            self.token_0_creator_chain_id,
            self.token_0,
            None,
            None,
            self.amount_0,
            self.amount_1,
            self.virtual_liquidity,
            self.to,
            None,
            false,
        );

        handler.handle().await
    }
}
