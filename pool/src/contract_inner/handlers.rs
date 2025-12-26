pub mod fund_pool_application_creation_chain;
pub mod message;
pub mod operation;
pub mod refund;
pub mod request_meme_fund;
pub mod transfer_meme_from_application;

use crate::interfaces::{parameters::ParametersInterface, state::StateInterface};
use abi::swap::pool::{PoolMessage, PoolOperation};
use base::handler::{Handler, HandlerError};
use message::{
    add_liquidity::AddLiquidityHandler as MessageAddLiquidityHandler,
    fund_fail::FundFailHandler as MessageFundFailHandler,
    fund_success::FundSuccessHandler as MessageFundSuccessHandler,
    new_transaction::NewTransactionHandler as MessageNewTransactionHandler,
    remove_liquidity::RemoveLiquidityHandler as MessageRemoveLiquidityHandler,
    request_fund::RequestFundHandler as MessageRequestFundHandler,
    set_fee_to::SetFeeToHandler as MessageSetFeeToHandler,
    set_fee_to_setter::SetFeeToSetterHandler as MessageSetFeeToSetterHandler,
    swap::SwapHandler as MessageSwapHandler,
};
use operation::{
    add_liquidity::AddLiquidityHandler as OperationAddLiquidityHandler,
    remove_liquidity::RemoveLiquidityHandler as OperationRemoveLiquidityHandler,
    set_fee_to::SetFeeToHandler as OperationSetFeeToHandler,
    set_fee_to_setter::SetFeeToSetterHandler as OperationSetFeeToSetterHandler,
    swap::SwapHandler as OperationSwapHandler,
};
use runtime::interfaces::{
    access_control::AccessControl, contract::ContractRuntimeContext, meme::MemeRuntimeContext,
};
use std::{cell::RefCell, rc::Rc};

pub struct HandlerFactory;

impl HandlerFactory {
    fn new_operation_handler(
        runtime: Rc<
            RefCell<
                impl ContractRuntimeContext
                    + AccessControl
                    + MemeRuntimeContext
                    + ParametersInterface
                    + ParametersInterface
                    + 'static,
            >,
        >,
        state: impl StateInterface + 'static,
        op: &PoolOperation,
    ) -> Box<dyn Handler<PoolMessage>> {
        match &op {
            PoolOperation::SetFeeTo { .. } => {
                Box::new(OperationSetFeeToHandler::new(runtime, state, op))
            }
            PoolOperation::SetFeeToSetter { .. } => {
                Box::new(OperationSetFeeToSetterHandler::new(runtime, state, op))
            }
            PoolOperation::AddLiquidity { .. } => {
                Box::new(OperationAddLiquidityHandler::new(runtime, state, op))
            }
            PoolOperation::RemoveLiquidity { .. } => {
                Box::new(OperationRemoveLiquidityHandler::new(runtime, state, op))
            }
            PoolOperation::Swap { .. } => Box::new(OperationSwapHandler::new(runtime, state, op)),
        }
    }

    fn new_message_handler(
        runtime: Rc<
            RefCell<
                impl ContractRuntimeContext
                    + AccessControl
                    + MemeRuntimeContext
                    + ParametersInterface
                    + 'static,
            >,
        >,
        state: impl StateInterface + 'static,
        msg: &PoolMessage,
    ) -> Box<dyn Handler<PoolMessage>> {
        match &msg {
            PoolMessage::RequestFund { .. } => {
                Box::new(MessageRequestFundHandler::new(runtime, state, msg))
            }
            PoolMessage::FundSuccess { .. } => {
                Box::new(MessageFundSuccessHandler::new(runtime, state, msg))
            }
            PoolMessage::FundFail { .. } => {
                Box::new(MessageFundFailHandler::new(runtime, state, msg))
            }
            PoolMessage::Swap { .. } => Box::new(MessageSwapHandler::new(runtime, state, msg)),
            PoolMessage::AddLiquidity { .. } => {
                Box::new(MessageAddLiquidityHandler::new(runtime, state, msg))
            }
            PoolMessage::RemoveLiquidity { .. } => {
                Box::new(MessageRemoveLiquidityHandler::new(runtime, state, msg))
            }
            PoolMessage::SetFeeTo { .. } => {
                Box::new(MessageSetFeeToHandler::new(runtime, state, msg))
            }
            PoolMessage::SetFeeToSetter { .. } => {
                Box::new(MessageSetFeeToSetterHandler::new(runtime, state, msg))
            }
            PoolMessage::NewTransaction { .. } => {
                Box::new(MessageNewTransactionHandler::new(runtime, state, msg))
            }
        }
    }

    pub fn new(
        runtime: Rc<
            RefCell<
                impl ContractRuntimeContext
                    + AccessControl
                    + MemeRuntimeContext
                    + ParametersInterface
                    + 'static,
            >,
        >,
        state: impl StateInterface + 'static,
        op: Option<&PoolOperation>,
        msg: Option<&PoolMessage>,
    ) -> Result<Box<dyn Handler<PoolMessage>>, HandlerError> {
        if let Some(op) = op {
            return Ok(HandlerFactory::new_operation_handler(runtime, state, op));
        }
        if let Some(msg) = msg {
            return Ok(HandlerFactory::new_message_handler(runtime, state, msg));
        }
        Err(HandlerError::InvalidOperationAndMessage)
    }
}
