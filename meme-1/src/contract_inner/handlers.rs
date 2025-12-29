pub mod message;
pub mod operation;

use crate::interfaces::{parameters::ParametersInterface, state::StateInterface};
use abi::meme::{MemeMessage, MemeOperation, MemeResponse};
use base::handler::{Handler, HandlerError};
use message::{
    approve::ApproveHandler as MessageApproveHandler,
    initialize_liquidity::InitializeLiquidityHandler as MessageInitializeLiquidityHandler,
    liquidity_funded::LiquidityFundedHandler as MessageLiquidityFundedHandler,
    mint::MintHandler as MessageMintHandler, transfer::TransferHandler as MessageTransferHandler,
    transfer_from::TransferFromHandler as MessageTransferFromHandler,
    transfer_from_application::TransferFromApplicationHandler as MessageTransferFromApplicationHandler,
    transfer_ownership::TransferOwnershipHandler as MessageTransferOwnershipHandler,
};
use operation::{
    approve::ApproveHandler as OperationApproveHandler,
    creator_chain_id::CreatorChainIdHandler as OperationCreatorChainIdHandler,
    initialize_liquidity::InitializeLiquidityHandler as OperationInitializeLiquidityHandler,
    mine::MineHandler as OperationMineHandler, mint::MintHandler as OperationMintHandler,
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
        state: impl StateInterface + 'static,
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
        }
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
        operation: &MemeOperation,
    ) -> bool {
        let chain_id = runtime.borrow_mut().chain_id();
        let application_creator_chain_id = runtime.borrow_mut().application_creator_chain_id();

        match operation {
            MemeOperation::Mine { .. } => chain_id == application_creator_chain_id,
            _ => true,
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
        if let Some(op) = op {
            // All operation must be run on right chain
            if !HandlerFactory::operation_executable(runtime.clone(), op) {
                return Err(HandlerError::NotAllowed);
            }

            return Ok(HandlerFactory::new_operation_handler(runtime, state, op));
        }
        if let Some(msg) = msg {
            // All messages must be run on user chain side
            if runtime.borrow_mut().only_application_creator().is_ok() {
                return Err(HandlerError::NotAllowed);
            }

            return Ok(HandlerFactory::new_message_handler(runtime, state, msg));
        }
        Err(HandlerError::InvalidOperationAndMessage)
    }
}
