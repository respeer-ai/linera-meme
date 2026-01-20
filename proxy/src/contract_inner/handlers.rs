pub mod message;
pub mod operation;

use crate::interfaces::state::StateInterface;
use abi::proxy::{ProxyMessage, ProxyOperation, ProxyResponse};
use base::handler::{Handler, HandlerError};
use message::{
    approve_add_genesis_miner::ApproveAddGenesisMinerHandler as MessageApproveAddGenesisMinerHandler,
    approve_add_operator::ApproveAddOperatorHandler as MessageApproveAddOperatorHandler,
    approve_ban_operator::ApproveBanOperatorHandler as MessageApproveBanOperatorHandler,
    approve_remove_genesis_miner::ApproveRemoveGenesisMinerHandler as MessageApproveRemoveGenesisMinerHandler,
    create_meme::CreateMemeHandler as MessageCreateMemeHandler,
    create_meme_ext::CreateMemeExtHandler as MessageCreateMemeExtHandler,
    deregister_miner::DeregisterMinerHandler as MessageDeregisterMinerHandler,
    meme_created::MemeCreatedHandler as MessageMemeCreatedHandler,
    propose_add_genesis_miner::ProposeAddGenesisMinerHandler as MessageProposeAddGenesisMinerHandler,
    propose_add_operator::ProposeAddOperatorHandler as MessageProposeAddOperatorHandler,
    propose_ban_operator::ProposeBanOperatorHandler as MessageProposeBanOperatorHandler,
    propose_remove_genesis_miner::ProposeRemoveGenesisMinerHandler as MessageProposeRemoveGenesisMinerHandler,
    register_miner::RegisterMinerHandler as MessageRegisterMinerHandler,
};
use operation::{
    approve_add_genesis_miner::ApproveAddGenesisMinerHandler as OperationApproveAddGenesisMinerHandler,
    approve_add_operator::ApproveAddOperatorHandler as OperationApproveAddOperatorHandler,
    approve_ban_operator::ApproveBanOperatorHandler as OperationApproveBanOperatorHandler,
    approve_remove_genesis_miner::ApproveRemoveGenesisMinerHandler as OperationApproveRemoveGenesisMinerHandler,
    create_meme::CreateMemeHandler as OperationCreateMemeHandler,
    deregister_miner::DeregisterMinerHandler as OperationDeregisterMinerHandler,
    open_multi_leader_rounds::OpenMultiLeaderRoundsHandler as OperationOpenMultiLeaderRoundsHandler,
    propose_add_genesis_miner::ProposeAddGenesisMinerHandler as OperationProposeAddGenesisMinerHandler,
    propose_add_operator::ProposeAddOperatorHandler as OperationProposeAddOperatorHandler,
    propose_ban_operator::ProposeBanOperatorHandler as OperationProposeBanOperatorHandler,
    propose_remove_genesis_miner::ProposeRemoveGenesisMinerHandler as OperationProposeRemoveGenesisMinerHandler,
    register_miner::RegisterMinerHandler as OperationRegisterMinerHandler,
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
        op: &ProxyOperation,
    ) -> Box<dyn Handler<ProxyMessage, ProxyResponse>> {
        match &op {
            ProxyOperation::ProposeAddGenesisMiner { .. } => Box::new(
                OperationProposeAddGenesisMinerHandler::new(runtime, state, op),
            ),
            ProxyOperation::ApproveAddGenesisMiner { .. } => Box::new(
                OperationApproveAddGenesisMinerHandler::new(runtime, state, op),
            ),
            ProxyOperation::ProposeRemoveGenesisMiner { .. } => Box::new(
                OperationProposeRemoveGenesisMinerHandler::new(runtime, state, op),
            ),
            ProxyOperation::ApproveRemoveGenesisMiner { .. } => Box::new(
                OperationApproveRemoveGenesisMinerHandler::new(runtime, state, op),
            ),
            ProxyOperation::RegisterMiner { .. } => {
                Box::new(OperationRegisterMinerHandler::new(runtime, state, op))
            }
            ProxyOperation::DeregisterMiner { .. } => {
                Box::new(OperationDeregisterMinerHandler::new(runtime, state, op))
            }
            ProxyOperation::CreateMeme { .. } => {
                Box::new(OperationCreateMemeHandler::new(runtime, state, op))
            }
            ProxyOperation::ProposeAddOperator { .. } => {
                Box::new(OperationProposeAddOperatorHandler::new(runtime, state, op))
            }
            ProxyOperation::ApproveAddOperator { .. } => {
                Box::new(OperationApproveAddOperatorHandler::new(runtime, state, op))
            }
            ProxyOperation::ProposeBanOperator { .. } => {
                Box::new(OperationProposeBanOperatorHandler::new(runtime, state, op))
            }
            ProxyOperation::ApproveBanOperator { .. } => {
                Box::new(OperationApproveBanOperatorHandler::new(runtime, state, op))
            }
            ProxyOperation::OpenMultiLeaderRounds { .. } => Box::new(
                OperationOpenMultiLeaderRoundsHandler::new(runtime, state, op),
            ),
        }
    }

    fn new_message_handler(
        runtime: Rc<
            RefCell<impl ContractRuntimeContext + AccessControl + MemeRuntimeContext + 'static>,
        >,
        state: impl StateInterface + 'static,
        msg: &ProxyMessage,
    ) -> Box<dyn Handler<ProxyMessage, ProxyResponse>> {
        match &msg {
            ProxyMessage::ProposeAddGenesisMiner { .. } => Box::new(
                MessageProposeAddGenesisMinerHandler::new(runtime, state, msg),
            ),
            ProxyMessage::ApproveAddGenesisMiner { .. } => Box::new(
                MessageApproveAddGenesisMinerHandler::new(runtime, state, msg),
            ),
            ProxyMessage::ProposeRemoveGenesisMiner { .. } => Box::new(
                MessageProposeRemoveGenesisMinerHandler::new(runtime, state, msg),
            ),
            ProxyMessage::ApproveRemoveGenesisMiner { .. } => Box::new(
                MessageApproveRemoveGenesisMinerHandler::new(runtime, state, msg),
            ),
            ProxyMessage::RegisterMiner { .. } => {
                Box::new(MessageRegisterMinerHandler::new(runtime, state, msg))
            }
            ProxyMessage::DeregisterMiner { .. } => {
                Box::new(MessageDeregisterMinerHandler::new(runtime, state, msg))
            }
            ProxyMessage::CreateMeme { .. } => {
                Box::new(MessageCreateMemeHandler::new(runtime, state, msg))
            }
            ProxyMessage::CreateMemeExt { .. } => {
                Box::new(MessageCreateMemeExtHandler::new(runtime, state, msg))
            }
            ProxyMessage::MemeCreated { .. } => {
                Box::new(MessageMemeCreatedHandler::new(runtime, state, msg))
            }
            ProxyMessage::ProposeAddOperator { .. } => {
                Box::new(MessageProposeAddOperatorHandler::new(runtime, state, msg))
            }
            ProxyMessage::ApproveAddOperator { .. } => {
                Box::new(MessageApproveAddOperatorHandler::new(runtime, state, msg))
            }
            ProxyMessage::ProposeBanOperator { .. } => {
                Box::new(MessageProposeBanOperatorHandler::new(runtime, state, msg))
            }
            ProxyMessage::ApproveBanOperator { .. } => {
                Box::new(MessageApproveBanOperatorHandler::new(runtime, state, msg))
            }
        }
    }

    fn message_executable(
        runtime: Rc<
            RefCell<impl ContractRuntimeContext + AccessControl + MemeRuntimeContext + 'static>,
        >,
        message: &ProxyMessage,
    ) -> bool {
        let chain_id = runtime.borrow_mut().chain_id();
        let application_creator_chain_id = runtime.borrow_mut().application_creator_chain_id();

        match message {
            ProxyMessage::CreateMemeExt { .. } => chain_id != application_creator_chain_id,
            _ => chain_id == application_creator_chain_id,
        }
    }

    pub fn new(
        runtime: Rc<
            RefCell<impl ContractRuntimeContext + AccessControl + MemeRuntimeContext + 'static>,
        >,
        state: impl StateInterface + 'static,
        op: Option<&ProxyOperation>,
        msg: Option<&ProxyMessage>,
    ) -> Result<Box<dyn Handler<ProxyMessage, ProxyResponse>>, HandlerError> {
        if let Some(op) = op {
            // All operations must be run on user chain side
            if runtime.borrow_mut().only_application_creator().is_ok() {
                return Err(HandlerError::NotAllowed);
            }

            return Ok(HandlerFactory::new_operation_handler(runtime, state, op));
        }
        if let Some(msg) = msg {
            // All messages must be run on right chain
            if !HandlerFactory::message_executable(runtime.clone(), msg) {
                return Err(HandlerError::NotAllowed);
            }

            return Ok(HandlerFactory::new_message_handler(runtime, state, msg));
        }
        Err(HandlerError::InvalidOperationAndMessage)
    }
}
