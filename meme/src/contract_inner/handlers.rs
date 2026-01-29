pub mod message;
pub mod open_multi_leader_rounds;
pub mod operation;

use crate::interfaces::{parameters::ParametersInterface, state::StateInterface};
use abi::meme::{MemeMessage, MemeOperation, MemeResponse};
use base::handler::{Handler, HandlerError};
use linera_sdk::linera_base_types::BlockHeight;
use message::{
    approve::ApproveHandler as MessageApproveHandler,
    initialize_liquidity::InitializeLiquidityHandler as MessageInitializeLiquidityHandler,
    liquidity_funded::LiquidityFundedHandler as MessageLiquidityFundedHandler,
    mint::MintHandler as MessageMintHandler, redeem::RedeemHandler as MessageRedeemHandler,
    transfer::TransferHandler as MessageTransferHandler,
    transfer_from::TransferFromHandler as MessageTransferFromHandler,
    transfer_from_application::TransferFromApplicationHandler as MessageTransferFromApplicationHandler,
    transfer_ownership::TransferOwnershipHandler as MessageTransferOwnershipHandler,
};
use operation::{
    approve::ApproveHandler as OperationApproveHandler,
    creator_chain_id::CreatorChainIdHandler as OperationCreatorChainIdHandler,
    initialize_liquidity::InitializeLiquidityHandler as OperationInitializeLiquidityHandler,
    mine::MineHandler as OperationMineHandler, mint::MintHandler as OperationMintHandler,
    redeem::RedeemHandler as OperationRedeemHandler,
    transfer::TransferHandler as OperationTransferHandler,
    transfer_from::TransferFromHandler as OperationTransferFromHandler,
    transfer_from_application::TransferFromApplicationHandler as OperationTransferFromApplicationHandler,
    transfer_ownership::TransferOwnershipHandler as OperationTransferOwnershipHandler,
    transfer_to_caller::TransferToCallerHandler as OperationTransferToCallerHandler,
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
        state: Rc<RefCell<impl StateInterface + 'static>>,
        op: &MemeOperation,
    ) -> Box<dyn Handler<MemeMessage, MemeResponse>> {
        match &op {
            MemeOperation::CreatorChainId { .. } => {
                Box::new(OperationCreatorChainIdHandler::new(runtime, state, op))
            }
            MemeOperation::Approve { .. } => {
                Box::new(OperationApproveHandler::new(runtime, state, op))
            }
            MemeOperation::InitializeLiquidity { .. } => {
                Box::new(OperationInitializeLiquidityHandler::new(runtime, state, op))
            }
            MemeOperation::Mine { .. } => Box::new(OperationMineHandler::new(runtime, state, op)),
            MemeOperation::Mint { .. } => Box::new(OperationMintHandler::new(runtime, state, op)),
            MemeOperation::Transfer { .. } => {
                Box::new(OperationTransferHandler::new(runtime, state, op))
            }
            MemeOperation::TransferFrom { .. } => {
                Box::new(OperationTransferFromHandler::new(runtime, state, op))
            }
            MemeOperation::TransferFromApplication { .. } => Box::new(
                OperationTransferFromApplicationHandler::new(runtime, state, op),
            ),
            MemeOperation::TransferOwnership { .. } => {
                Box::new(OperationTransferOwnershipHandler::new(runtime, state, op))
            }
            MemeOperation::TransferToCaller { .. } => {
                Box::new(OperationTransferToCallerHandler::new(runtime, state, op))
            }
            MemeOperation::Redeem { .. } => {
                Box::new(OperationRedeemHandler::new(runtime, state, op))
            }
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
        state: Rc<RefCell<impl StateInterface + 'static>>,
        msg: &MemeMessage,
    ) -> Box<dyn Handler<MemeMessage, MemeResponse>> {
        match &msg {
            MemeMessage::LiquidityFunded { .. } => {
                Box::new(MessageLiquidityFundedHandler::new(runtime, state, msg))
            }
            MemeMessage::Approve { .. } => {
                Box::new(MessageApproveHandler::new(runtime, state, msg))
            }
            MemeMessage::InitializeLiquidity { .. } => {
                Box::new(MessageInitializeLiquidityHandler::new(runtime, state, msg))
            }
            MemeMessage::Mint { .. } => Box::new(MessageMintHandler::new(runtime, state, msg)),
            MemeMessage::Transfer { .. } => {
                Box::new(MessageTransferHandler::new(runtime, state, msg))
            }
            MemeMessage::TransferFrom { .. } => {
                Box::new(MessageTransferFromHandler::new(runtime, state, msg))
            }
            MemeMessage::TransferFromApplication { .. } => Box::new(
                MessageTransferFromApplicationHandler::new(runtime, state, msg),
            ),
            MemeMessage::TransferOwnership { .. } => {
                Box::new(MessageTransferOwnershipHandler::new(runtime, state, msg))
            }
            MemeMessage::Redeem { .. } => Box::new(MessageRedeemHandler::new(runtime, state, msg)),
        }
    }

    fn is_valid_mining_height(
        runtime: Rc<
            RefCell<
                impl ContractRuntimeContext
                    + AccessControl
                    + MemeRuntimeContext
                    + ParametersInterface
                    + 'static,
            >,
        >,
        state: Rc<RefCell<impl StateInterface + 'static>>,
    ) -> bool {
        if !runtime.borrow_mut().enable_mining() || state.borrow().maybe_mining_info().is_none() {
            return true;
        }

        let block_height = runtime.borrow_mut().block_height();
        let chain_id = runtime.borrow_mut().chain_id();
        let application_creator_chain_id = runtime.borrow_mut().application_creator_chain_id();
        let mining_height = state.borrow().mining_height();
        let mining_started = state.borrow().is_mining_started();

        // Mine operation will be the first operation of the block proposal and it'll set mining_height
        // For other operations, if the heights are different, they will fail to execute
        // Mining height is always the next block height, not the executing one
        chain_id != application_creator_chain_id
            || !mining_started
            || mining_height == block_height.saturating_add(BlockHeight(1))
    }

    fn operation_executable(
        runtime: Rc<
            RefCell<
                impl ContractRuntimeContext
                    + AccessControl
                    + MemeRuntimeContext
                    + ParametersInterface
                    + 'static,
            >,
        >,
        state: Rc<RefCell<impl StateInterface + 'static>>,
        operation: &MemeOperation,
    ) -> bool {
        let chain_id = runtime.borrow_mut().chain_id();
        let application_creator_chain_id = runtime.borrow_mut().application_creator_chain_id();

        match operation {
            MemeOperation::Mine { .. } => chain_id == application_creator_chain_id,
            _ => HandlerFactory::is_valid_mining_height(runtime, state),
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
        op: Option<&MemeOperation>,
        msg: Option<&MemeMessage>,
    ) -> Result<Box<dyn Handler<MemeMessage, MemeResponse>>, HandlerError> {
        let state = Rc::new(RefCell::new(state));

        if let Some(op) = op {
            // All operation must be run on right chain
            if !HandlerFactory::operation_executable(runtime.clone(), state.clone(), op) {
                return Err(HandlerError::NotAllowed);
            }

            return Ok(HandlerFactory::new_operation_handler(runtime, state, op));
        }
        if let Some(msg) = msg {
            // All messages must be run on user chain side
            if runtime.borrow_mut().only_application_creator().is_err()
                || !HandlerFactory::is_valid_mining_height(runtime.clone(), state.clone())
            {
                return Err(HandlerError::NotAllowed);
            }

            return Ok(HandlerFactory::new_message_handler(runtime, state, msg));
        }
        Err(HandlerError::InvalidOperationAndMessage)
    }
}
