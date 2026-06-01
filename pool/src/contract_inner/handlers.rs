pub mod fund_pool_application_creation_chain;
pub mod message;
pub mod operation;
pub mod refund;
pub mod request_meme_fund;
pub mod request_meme_fund_ext;
pub mod transfer_meme_from_application;

use crate::interfaces::{parameters::ParametersInterface, state::StateInterface};
use abi::swap::pool::{PoolMessage, PoolOperation, PoolResponse};
use base::handler::{Handler, HandlerError};
use message::{
    add_liquidity::AddLiquidityHandler as MessageAddLiquidityHandler,
    add_liquidity_transfer_receipt::AddLiquidityTransferReceiptHandler as MessageAddLiquidityTransferReceiptHandler,
    claim::ClaimHandler as MessageClaimHandler,
    fund_fail::FundFailHandler as MessageFundFailHandler,
    fund_result_ext::FundResultExtHandler as MessageFundResultExtHandler,
    fund_success::FundSuccessHandler as MessageFundSuccessHandler,
    initialize_liquidity::InitializeLiquidityHandler as MessageInitializeLiquidityHandler,
    new_transaction::NewTransactionHandler as MessageNewTransactionHandler,
    remove_liquidity::RemoveLiquidityHandler as MessageRemoveLiquidityHandler,
    request_fund::RequestFundHandler as MessageRequestFundHandler,
    request_fund_ext::RequestFundExtHandler as MessageRequestFundExtHandler,
    set_fee_to::SetFeeToHandler as MessageSetFeeToHandler,
    set_fee_to_setter::SetFeeToSetterHandler as MessageSetFeeToSetterHandler,
    swap::SwapHandler as MessageSwapHandler,
};
use operation::{
    add_liquidity::AddLiquidityHandler as OperationAddLiquidityHandler,
    add_liquidity_transfer_receipt::AddLiquidityTransferReceiptHandler as OperationAddLiquidityTransferReceiptHandler,
    claim::ClaimHandler as OperationClaimHandler,
    claim_transfer_receipt::ClaimTransferReceiptHandler as OperationClaimTransferReceiptHandler,
    initialize_liquidity::InitializeLiquidityHandler as OperationInitializeLiquidityHandler,
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
                    + 'static,
            >,
        >,
        state: impl StateInterface + 'static,
        op: &PoolOperation,
    ) -> Box<dyn Handler<PoolMessage, PoolResponse>> {
        match &op {
            PoolOperation::SetFeeTo { .. } => {
                Box::new(OperationSetFeeToHandler::new(runtime, state, op))
            }
            PoolOperation::SetFeeToSetter { .. } => {
                Box::new(OperationSetFeeToSetterHandler::new(runtime, state, op))
            }
            PoolOperation::InitializeLiquidity { .. } => {
                Box::new(OperationInitializeLiquidityHandler::new(runtime, state, op))
            }
            PoolOperation::AddLiquidity { .. } => {
                Box::new(OperationAddLiquidityHandler::new(runtime, state, op))
            }
            PoolOperation::RemoveLiquidity { .. } => {
                Box::new(OperationRemoveLiquidityHandler::new(runtime, state, op))
            }
            PoolOperation::Swap { .. } => Box::new(OperationSwapHandler::new(runtime, state, op)),
            PoolOperation::Claim { .. } => Box::new(OperationClaimHandler::new(runtime, state, op)),
            PoolOperation::ClaimTransferReceipt { .. } => Box::new(
                OperationClaimTransferReceiptHandler::new(runtime, state, op),
            ),
            PoolOperation::AddLiquidityTransferReceipt { .. } => Box::new(
                OperationAddLiquidityTransferReceiptHandler::new(runtime, state, op),
            ),
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
    ) -> Box<dyn Handler<PoolMessage, PoolResponse>> {
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
            PoolMessage::RequestFundExt { .. } => {
                Box::new(MessageRequestFundExtHandler::new(runtime, state, msg))
            }
            PoolMessage::FundResultExt { .. } => {
                Box::new(MessageFundResultExtHandler::new(runtime, state, msg))
            }
            PoolMessage::AddLiquidityTransferReceipt { .. } => Box::new(
                MessageAddLiquidityTransferReceiptHandler::new(runtime, state, msg),
            ),
            PoolMessage::Swap { .. } => Box::new(MessageSwapHandler::new(runtime, state, msg)),
            PoolMessage::AddLiquidity { .. } => {
                Box::new(MessageAddLiquidityHandler::new(runtime, state, msg))
            }
            PoolMessage::InitializeLiquidity { .. } => {
                Box::new(MessageInitializeLiquidityHandler::new(runtime, state, msg))
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
            PoolMessage::Claim { .. } => Box::new(MessageClaimHandler::new(runtime, state, msg)),
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
    ) -> Result<Box<dyn Handler<PoolMessage, PoolResponse>>, HandlerError> {
        if let Some(op) = op {
            return Ok(HandlerFactory::new_operation_handler(runtime, state, op));
        }
        if let Some(msg) = msg {
            return Ok(HandlerFactory::new_message_handler(runtime, state, msg));
        }
        Err(HandlerError::InvalidOperationAndMessage)
    }
}
