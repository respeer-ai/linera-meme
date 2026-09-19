pub mod message;
pub mod operation;
pub mod fund_pool_application_creation_chain;
pub mod refund;
pub mod request_meme_fund;
pub mod transfer_meme_from_application;

use abi::application_state_base::PublicStateBaseInterface;
use abi::pool::{PoolMessage, PoolOperation, PoolResponse};
use base::handler::{Handler, HandlerError};
use runtime::interfaces::{
    access_control::AccessControl, contract::ContractRuntimeContext, meme::MemeRuntimeContext,
};
use std::{cell::RefCell, rc::Rc};

use crate::interfaces::{parameters::ParametersInterface, state::StateInterface};

use message::{
    add_liquidity::AddLiquidityHandler as MessageAddLiquidityHandler,
    add_liquidity_transfer_receipt::AddLiquidityTransferReceiptHandler
        as MessageAddLiquidityTransferReceiptHandler,
    claim::ClaimHandler as MessageClaimHandler,
    claim_transfer_receipt::ClaimTransferReceiptHandler as MessageClaimTransferReceiptHandler,
    fund_result::FundResultHandler as MessageFundResultHandler,
    initialize_liquidity::InitializeLiquidityHandler as MessageInitializeLiquidityHandler,
    new_transaction::NewTransactionHandler as MessageNewTransactionHandler,
    remove_liquidity::RemoveLiquidityHandler as MessageRemoveLiquidityHandler,
    request_fund::RequestFundHandler as MessageRequestFundHandler,
    set_fee_to::SetFeeToHandler as MessageSetFeeToHandler,
    set_fee_to_setter::SetFeeToSetterHandler as MessageSetFeeToSetterHandler,
    swap::SwapHandler as MessageSwapHandler,
    swap_transfer_receipt::SwapTransferReceiptHandler as MessageSwapTransferReceiptHandler,
};
use operation::{
    add_liquidity::AddLiquidityHandler,
    add_liquidity_transfer_receipt::AddLiquidityTransferReceiptHandler,
    append_state::AppendStateHandler, append_states::AppendStatesHandler,
    claim::ClaimHandler, claim_transfer_receipt::ClaimTransferReceiptHandler,
    handoff::HandoffHandler, initialize::InitializeHandler,
    initialize_liquidity::InitializeLiquidityHandler,
    remove_liquidity::RemoveLiquidityHandler, set_fee_to::SetFeeToHandler,
    set_fee_to_setter::SetFeeToSetterHandler, set_operator::SetOperatorHandler,
    swap::SwapHandler, swap_transfer_receipt::SwapTransferReceiptHandler,
};

pub struct HandlerFactory;

impl HandlerFactory {
    pub fn new(
        runtime: Rc<
            RefCell<
                impl ContractRuntimeContext + AccessControl + ParametersInterface + MemeRuntimeContext + 'static,
            >,
        >,
        state: impl StateInterface + PublicStateBaseInterface + Clone + 'static,
        operation: Option<&PoolOperation>,
        message: Option<&PoolMessage>,
    ) -> Result<Box<dyn Handler<PoolMessage, PoolResponse>>, HandlerError> {
        if let Some(operation) = operation {
            return Ok(Self::new_operation_handler(runtime, state, operation));
        }
        if let Some(message) = message {
            return Ok(Self::new_message_handler(runtime, state, message));
        }
        Err(HandlerError::InvalidOperationAndMessage)
    }

    fn new_message_handler(
        runtime: Rc<
            RefCell<
                impl ContractRuntimeContext + AccessControl + ParametersInterface + MemeRuntimeContext + 'static,
            >,
        >,
        state: impl StateInterface + PublicStateBaseInterface + Clone + 'static,
        msg: &PoolMessage,
    ) -> Box<dyn Handler<PoolMessage, PoolResponse>> {
        match msg {
            PoolMessage::SetFeeTo { .. } => Box::new(MessageSetFeeToHandler::new(runtime, state, msg)),
            PoolMessage::SetFeeToSetter { .. } => Box::new(MessageSetFeeToSetterHandler::new(
                runtime, state, msg,
            )),
            PoolMessage::InitializeLiquidity { .. } => Box::new(
                MessageInitializeLiquidityHandler::new(runtime, state, msg),
            ),
            PoolMessage::AddLiquidity { .. } => {
                Box::new(MessageAddLiquidityHandler::new(runtime, state, msg))
            }
            PoolMessage::AddLiquidityTransferReceipt { .. } => Box::new(
                MessageAddLiquidityTransferReceiptHandler::new(runtime, state, msg),
            ),
            PoolMessage::RemoveLiquidity { .. } => Box::new(
                MessageRemoveLiquidityHandler::new(runtime, state, msg),
            ),
            PoolMessage::Swap { .. } => Box::new(MessageSwapHandler::new(runtime, state, msg)),
            PoolMessage::SwapTransferReceipt { .. } => Box::new(
                MessageSwapTransferReceiptHandler::new(runtime, state, msg),
            ),
            PoolMessage::Claim { .. } => Box::new(MessageClaimHandler::new(runtime, state, msg)),
            PoolMessage::ClaimTransferReceipt { .. } => Box::new(
                MessageClaimTransferReceiptHandler::new(runtime, state, msg),
            ),
            PoolMessage::FundResult { .. } => {
                Box::new(MessageFundResultHandler::new(runtime, state, msg))
            }
            PoolMessage::NewTransaction { .. } => {
                Box::new(MessageNewTransactionHandler::new(runtime, state, msg))
            }
            PoolMessage::RequestFund { .. } => {
                Box::new(MessageRequestFundHandler::new(runtime, state, msg))
            }
        }
    }

    fn new_operation_handler(
        runtime: Rc<
            RefCell<
                impl ContractRuntimeContext + AccessControl + ParametersInterface + MemeRuntimeContext + 'static,
            >,
        >,
        state: impl StateInterface + PublicStateBaseInterface + Clone + 'static,
        op: &PoolOperation,
    ) -> Box<dyn Handler<PoolMessage, PoolResponse>> {
        match op {
            PoolOperation::Initialize { .. } => Box::new(InitializeHandler::new(runtime, state, op)),
            PoolOperation::AppendState { .. } => {
                Box::new(AppendStateHandler::new(runtime, state, op))
            }
            PoolOperation::AppendStates { .. } => {
                Box::new(AppendStatesHandler::new(runtime, state, op))
            }
            PoolOperation::Handoff { .. } => Box::new(HandoffHandler::new(runtime, state, op)),
            PoolOperation::SetOperator { .. } => {
                Box::new(SetOperatorHandler::new(runtime, state, op))
            }
            PoolOperation::SetFeeTo { .. } => {
                Box::new(SetFeeToHandler::new(runtime, state, op))
            }
            PoolOperation::SetFeeToSetter { .. } => Box::new(SetFeeToSetterHandler::new(
                runtime, state, op,
            )),
            PoolOperation::InitializeLiquidity { .. } => Box::new(
                InitializeLiquidityHandler::new(runtime, state, op),
            ),
            PoolOperation::AddLiquidity { .. } => {
                Box::new(AddLiquidityHandler::new(runtime, state, op))
            }
            PoolOperation::AddLiquidityTransferReceipt { .. } => Box::new(
                AddLiquidityTransferReceiptHandler::new(runtime, state, op),
            ),
            PoolOperation::RemoveLiquidity { .. } => {
                Box::new(RemoveLiquidityHandler::new(runtime, state, op))
            }
            PoolOperation::Swap { .. } => Box::new(SwapHandler::new(runtime, state, op)),
            PoolOperation::SwapTransferReceipt { .. } => Box::new(
                SwapTransferReceiptHandler::new(runtime, state, op),
            ),
            PoolOperation::Claim { .. } => Box::new(ClaimHandler::new(runtime, state, op)),
            PoolOperation::ClaimTransferReceipt { .. } => Box::new(
                ClaimTransferReceiptHandler::new(runtime, state, op),
            ),
        }
    }
}
