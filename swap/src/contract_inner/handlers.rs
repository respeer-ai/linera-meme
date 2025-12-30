pub mod create_pool;
pub mod message;
pub mod operation;

use crate::interfaces::state::StateInterface;
use abi::swap::router::{SwapMessage, SwapOperation, SwapResponse};
use base::handler::Handler;
use base::handler::HandlerError;
use message::{
    create_pool::CreatePoolHandler as MessageCreatePoolHandler,
    create_user_pool::CreateUserPoolHandler as MessageCreateUserPoolHandler,
    initialize_liquidity::InitializeLiquidityHandler as MessageInitializeLiquidityHandler,
    pool_created::PoolCreatedHandler as MessagePoolCreatedHandler,
    update_pool::UpdatePoolHandler as MessageUpdatePoolHandler,
    user_pool_created::UserPoolCreatedHandler as MessageUserPoolCreatedHandler,
};
use operation::{
    create_pool::CreatePoolHandler as OperationCreatePoolHandler,
    initialize_liquidity::InitializeLiquidityHandler as OperationInitializeLiquidityHandler,
    update_pool::UpdatePoolHandler as OperationUpdatePoolHandler,
};
use runtime::interfaces::{
    access_control::AccessControl, contract::ContractRuntimeContext, meme::MemeRuntimeContext,
};
use std::{cell::RefCell, rc::Rc};

pub struct HandlerFactory;

impl HandlerFactory {
    fn new_operation_handler(
        runtime: Rc<
            RefCell<impl ContractRuntimeContext + AccessControl + MemeRuntimeContext + 'static>,
        >,
        state: impl StateInterface + 'static,
        op: &SwapOperation,
    ) -> Box<dyn Handler<SwapMessage, SwapResponse>> {
        match &op {
            SwapOperation::CreatePool { .. } => {
                Box::new(OperationCreatePoolHandler::new(runtime, state, op))
            }
            SwapOperation::InitializeLiquidity { .. } => {
                Box::new(OperationInitializeLiquidityHandler::new(runtime, state, op))
            }
            SwapOperation::UpdatePool { .. } => {
                Box::new(OperationUpdatePoolHandler::new(runtime, state, op))
            }
        }
    }

    fn new_message_handler(
        runtime: Rc<
            RefCell<impl ContractRuntimeContext + AccessControl + MemeRuntimeContext + 'static>,
        >,
        state: impl StateInterface + 'static,
        msg: &SwapMessage,
    ) -> Box<dyn Handler<SwapMessage, SwapResponse>> {
        match &msg {
            SwapMessage::CreatePool { .. } => {
                Box::new(MessageCreatePoolHandler::new(runtime, state, msg))
            }
            SwapMessage::CreateUserPool { .. } => {
                Box::new(MessageCreateUserPoolHandler::new(runtime, state, msg))
            }
            SwapMessage::InitializeLiquidity { .. } => {
                Box::new(MessageInitializeLiquidityHandler::new(runtime, state, msg))
            }
            SwapMessage::PoolCreated { .. } => {
                Box::new(MessagePoolCreatedHandler::new(runtime, state, msg))
            }
            SwapMessage::UpdatePool { .. } => {
                Box::new(MessageUpdatePoolHandler::new(runtime, state, msg))
            }
            SwapMessage::UserPoolCreated { .. } => {
                Box::new(MessageUserPoolCreatedHandler::new(runtime, state, msg))
            }
        }
    }

    pub fn new(
        runtime: Rc<
            RefCell<impl ContractRuntimeContext + AccessControl + MemeRuntimeContext + 'static>,
        >,
        state: impl StateInterface + 'static,
        op: Option<&SwapOperation>,
        msg: Option<&SwapMessage>,
    ) -> Result<Box<dyn Handler<SwapMessage, SwapResponse>>, HandlerError> {
        if let Some(op) = op {
            return Ok(HandlerFactory::new_operation_handler(runtime, state, op));
        }
        if let Some(msg) = msg {
            return Ok(HandlerFactory::new_message_handler(runtime, state, msg));
        }
        Err(HandlerError::InvalidOperationAndMessage)
    }
}
