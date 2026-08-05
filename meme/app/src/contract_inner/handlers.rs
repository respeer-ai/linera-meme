pub mod message;
pub mod open_multi_leader_rounds;
pub mod operation;

use crate::interfaces::{parameters::ParametersInterface, state::StateInterface};
use abi::{
    application_state_base::PublicStateBaseInterface,
    meme::{MemeMessage, MemeOperation, MemeResponse},
};
use base::handler::{Handler, HandlerError};
use linera_sdk::linera_base_types::BlockHeight;
use message::{
    approve::ApproveHandler as MessageApproveHandler,
    initialize_liquidity::InitializeLiquidityHandler as MessageInitializeLiquidityHandler,
    liquidity_funded::LiquidityFundedHandler as MessageLiquidityFundedHandler,
    mint::MintHandler as MessageMintHandler,
    redeem::RedeemHandler as MessageRedeemHandler,
    transfer::TransferHandler as MessageTransferHandler,
    transfer_from::TransferFromHandler as MessageTransferFromHandler,
    transfer_from_application::TransferFromApplicationHandler as MessageTransferFromApplicationHandler,
    transfer_from_application_receipt::TransferFromApplicationReceiptHandler as MessageTransferFromApplicationReceiptHandler,
    transfer_from_application_with_receipt::TransferFromApplicationWithReceiptHandler as MessageTransferFromApplicationWithReceiptHandler,
    transfer_ownership::TransferOwnershipHandler as MessageTransferOwnershipHandler,
};
use operation::{
    append_state::AppendStateHandler, append_states::AppendStatesHandler,
    approve::ApproveHandler as OperationApproveHandler,
    handoff::HandoffHandler,
    initialize::InitializeHandler as OperationInitializeHandler,
    initialize_liquidity::InitializeLiquidityHandler,
    mine::MineHandler as OperationMineHandler, mint::MintHandler as OperationMintHandler,
    redeem::RedeemHandler as OperationRedeemHandler,
    set_operator::SetOperatorHandler as OperationSetOperatorHandler,
    transfer::TransferHandler as OperationTransferHandler,
    transfer_from::TransferFromHandler as OperationTransferFromHandler,
    transfer_from_application::TransferFromApplicationHandler as OperationTransferFromApplicationHandler,
    transfer_from_application_with_receipt::TransferFromApplicationWithReceiptHandler as OperationTransferFromApplicationWithReceiptHandler,
    transfer_ownership::TransferOwnershipHandler as OperationTransferOwnershipHandler,
    transfer_to_caller::TransferToCallerHandler as OperationTransferToCallerHandler,
};
use runtime::interfaces::{access_control::AccessControl, contract::ContractRuntimeContext};
use std::{cell::RefCell, rc::Rc};

pub struct HandlerFactory;

impl HandlerFactory {
    fn new_operation_handler(
        runtime: Rc<RefCell<impl ContractRuntimeContext + AccessControl + ParametersInterface + 'static>>,
        state: impl StateInterface + PublicStateBaseInterface + 'static,
        op: &MemeOperation,
    ) -> Box<dyn Handler<MemeMessage, MemeResponse>> {
        match op {
            MemeOperation::SetOperator { .. } => Box::new(OperationSetOperatorHandler::new(
                runtime, state, op,
            )),
            MemeOperation::Transfer { .. } => {
                Box::new(OperationTransferHandler::new(runtime, state, op))
            }
            MemeOperation::TransferFrom { .. } => {
                Box::new(OperationTransferFromHandler::new(runtime, state, op))
            }
            MemeOperation::TransferFromApplication { .. } => Box::new(
                OperationTransferFromApplicationHandler::new(runtime, state, op),
            ),
            MemeOperation::TransferFromApplicationWithReceipt { .. } => Box::new(
                OperationTransferFromApplicationWithReceiptHandler::new(runtime, state, op),
            ),
            MemeOperation::Approve { .. } => {
                Box::new(OperationApproveHandler::new(runtime, state, op))
            }
            MemeOperation::Mint { .. } => Box::new(OperationMintHandler::new(runtime, state, op)),
            MemeOperation::Redeem { .. } => {
                Box::new(OperationRedeemHandler::new(runtime, state, op))
            }
            MemeOperation::Mine { .. } => Box::new(OperationMineHandler::new(runtime, state, op)),
            MemeOperation::TransferOwnership { .. } => Box::new(
                OperationTransferOwnershipHandler::new(runtime, state, op),
            ),
            MemeOperation::AppendState { .. } => {
                Box::new(AppendStateHandler::new(runtime, state, op))
            }
            MemeOperation::AppendStates { .. } => {
                Box::new(AppendStatesHandler::new(runtime, state, op))
            }
            MemeOperation::Handoff { .. } => Box::new(HandoffHandler::new(runtime, state, op)),
            MemeOperation::InitializeLiquidity { .. } => {
                Box::new(InitializeLiquidityHandler::new(runtime, state, op))
            }
            MemeOperation::TransferToCaller { .. } => Box::new(
                OperationTransferToCallerHandler::new(runtime, state, op),
            ),
            MemeOperation::Initialize { .. } => {
                Box::new(OperationInitializeHandler::new(runtime, state, op))
            }
        }
    }

    fn new_message_handler(
        runtime: Rc<RefCell<impl ContractRuntimeContext + AccessControl + ParametersInterface + 'static>>,
        state: impl StateInterface + PublicStateBaseInterface + Clone + 'static,
        msg: &MemeMessage,
    ) -> Box<dyn Handler<MemeMessage, MemeResponse>> {
        match msg {
            MemeMessage::Transfer { .. } => {
                Box::new(MessageTransferHandler::new(runtime, state, msg))
            }
            MemeMessage::TransferFrom { .. } => {
                Box::new(MessageTransferFromHandler::new(runtime, state, msg))
            }
            MemeMessage::TransferFromApplication { .. } => Box::new(
                MessageTransferFromApplicationHandler::new(runtime, state, msg),
            ),
            MemeMessage::TransferFromApplicationWithReceipt { .. } => Box::new(
                MessageTransferFromApplicationWithReceiptHandler::new(runtime, state, msg),
            ),
            MemeMessage::TransferFromApplicationReceipt { .. } => Box::new(
                MessageTransferFromApplicationReceiptHandler::new(runtime, state, msg),
            ),
            MemeMessage::Approve { .. } => {
                Box::new(MessageApproveHandler::new(runtime, state, msg))
            }
            MemeMessage::Mint { .. } => Box::new(MessageMintHandler::new(runtime, state, msg)),
            MemeMessage::Redeem { .. } => Box::new(MessageRedeemHandler::new(runtime, state, msg)),
            MemeMessage::TransferOwnership { .. } => Box::new(
                MessageTransferOwnershipHandler::new(runtime, state, msg),
            ),
            MemeMessage::InitializeLiquidity { .. } => Box::new(
                MessageInitializeLiquidityHandler::new(runtime, state, msg),
            ),
            MemeMessage::LiquidityFunded => {
                Box::new(MessageLiquidityFundedHandler::new(runtime, state, msg))
            }
        }
    }

    async fn is_valid_mining_height(
        runtime: Rc<
            RefCell<impl ContractRuntimeContext + AccessControl + ParametersInterface + 'static>,
        >,
        state: &impl StateInterface,
    ) -> bool {
        if !runtime.borrow_mut().enable_mining() {
            return true;
        }

        let Ok(mining_info) = state.mining_info().await else {
            return true;
        };

        let block_height = runtime.borrow_mut().block_height();
        let chain_id = runtime.borrow_mut().chain_id();
        let application_creator_chain_id = runtime.borrow_mut().application_creator_chain_id();

        chain_id != application_creator_chain_id
            || !mining_info.mining_started
            || mining_info.mining_height == block_height.saturating_add(BlockHeight(1))
    }

    async fn operation_executable(
        runtime: Rc<
            RefCell<impl ContractRuntimeContext + AccessControl + ParametersInterface + 'static>,
        >,
        state: &impl StateInterface,
        operation: &MemeOperation,
    ) -> bool {
        let chain_id = runtime.borrow_mut().chain_id();
        let application_creator_chain_id = runtime.borrow_mut().application_creator_chain_id();

        match operation {
            MemeOperation::Mine { .. } => chain_id == application_creator_chain_id,
            _ => Self::is_valid_mining_height(runtime, state).await,
        }
    }

    pub async fn new(
        runtime: Rc<RefCell<impl ContractRuntimeContext + AccessControl + ParametersInterface + 'static>>,
        state: impl StateInterface + PublicStateBaseInterface + Clone + 'static,
        op: Option<&MemeOperation>,
        msg: Option<&MemeMessage>,
    ) -> Result<Box<dyn Handler<MemeMessage, MemeResponse>>, HandlerError> {
        if let Some(op) = op {
            if !Self::operation_executable(runtime.clone(), &state, op).await {
                return Err(HandlerError::NotAllowed);
            }
            return Ok(Self::new_operation_handler(runtime, state, op));
        }
        if let Some(msg) = msg {
            let executable = match msg {
                MemeMessage::TransferFromApplicationReceipt { .. } => true,
                _ => {
                    runtime.borrow_mut().only_application_creator().is_ok()
                        && Self::is_valid_mining_height(runtime.clone(), &state).await
                }
            };
            if !executable {
                return Err(HandlerError::NotAllowed);
            }
            return Ok(Self::new_message_handler(runtime, state, msg));
        }
        Err(HandlerError::InvalidOperationAndMessage)
    }
}
