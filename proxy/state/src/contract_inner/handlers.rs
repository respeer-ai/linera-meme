pub mod operation;

use abi::proxy::state_v1::{ProxyStateV1Operation, ProxyStateV1Response};
use base::handler::{Handler, HandlerError};
use runtime::interfaces::{access_control::AccessControl, contract::ContractRuntimeContext};
use std::{cell::RefCell, rc::Rc};

use crate::interfaces::state::StateInterface;

use operation::{
    add_genesis_miner::AddGenesisMinerHandler,
    add_operator::AddOperatorHandler,
    approve_add_genesis_miner::ApproveAddGenesisMinerHandler,
    approve_add_operator::ApproveAddOperatorHandler,
    approve_ban_operator::ApproveBanOperatorHandler,
    approve_remove_genesis_miner::ApproveRemoveGenesisMinerHandler,
    ban_operator::BanOperatorHandler,
    bytecode::{MemeBytecodeIdHandler, MemeStateBytecodeIdsHandler, SwapApplicationIdHandler},
    chain_read::{ChainByTokenHandler, ChainHandler, ChainsHandler},
    create_chain::CreateChainHandler,
    create_chain_token::CreateChainTokenHandler,
    deregister_miner::DeregisterMinerHandler,
    handoff::HandoffHandler,
    initialize::InitializeHandler,
    miner_read::{GenesisMinersHandler, IsGenesisMinerHandler, MinerOwnersHandler, MinersHandler},
    register_miner::RegisterMinerHandler,
    remove_genesis_miner::RemoveGenesisMinerHandler,
    set_meme_bytecode_ids::SetMemeBytecodeIdsHandler,
    set_operator::SetOperatorHandler,
    validate_operator::ValidateOperatorHandler,
};

pub struct HandlerFactory;

impl HandlerFactory {
    pub fn new(
        runtime: Rc<RefCell<impl ContractRuntimeContext<Message = ()> + AccessControl + 'static>>,
        state: impl StateInterface + 'static,
        operation: Option<&ProxyStateV1Operation>,
        message: Option<&()>,
    ) -> Result<Box<dyn Handler<(), ProxyStateV1Response>>, HandlerError> {
        if let Some(operation) = operation {
            return Self::new_operation_handler(runtime, state, operation);
        }
        if message.is_some() {
            return Err(HandlerError::NotImplemented);
        }
        Err(HandlerError::InvalidOperationAndMessage)
    }

    fn new_operation_handler(
        runtime: Rc<RefCell<impl ContractRuntimeContext<Message = ()> + AccessControl + 'static>>,
        state: impl StateInterface + 'static,
        operation: &ProxyStateV1Operation,
    ) -> Result<Box<dyn Handler<(), ProxyStateV1Response>>, HandlerError> {
        match operation {
            ProxyStateV1Operation::Initialize { .. } => Ok(Box::new(
                InitializeHandler::new(runtime, state, operation),
            )),

            ProxyStateV1Operation::SetMemeBytecodeIds { .. } => Ok(Box::new(
                SetMemeBytecodeIdsHandler::new(runtime, state, operation),
            )),
            ProxyStateV1Operation::AddOperator { .. } => {
                Ok(Box::new(AddOperatorHandler::new(runtime, state, operation)))
            }
            ProxyStateV1Operation::ApproveAddOperator { .. } => Ok(Box::new(
                ApproveAddOperatorHandler::new(runtime, state, operation),
            )),
            ProxyStateV1Operation::BanOperator { .. } => {
                Ok(Box::new(BanOperatorHandler::new(runtime, state, operation)))
            }
            ProxyStateV1Operation::ApproveBanOperator { .. } => Ok(Box::new(
                ApproveBanOperatorHandler::new(runtime, state, operation),
            )),
            ProxyStateV1Operation::AddGenesisMiner { .. } => Ok(Box::new(
                AddGenesisMinerHandler::new(runtime, state, operation),
            )),
            ProxyStateV1Operation::ApproveAddGenesisMiner { .. } => Ok(Box::new(
                ApproveAddGenesisMinerHandler::new(runtime, state, operation),
            )),
            ProxyStateV1Operation::RemoveGenesisMiner { .. } => Ok(Box::new(
                RemoveGenesisMinerHandler::new(runtime, state, operation),
            )),
            ProxyStateV1Operation::ApproveRemoveGenesisMiner { .. } => Ok(Box::new(
                ApproveRemoveGenesisMinerHandler::new(runtime, state, operation),
            )),
            ProxyStateV1Operation::RegisterMiner { .. } => {
                Ok(Box::new(RegisterMinerHandler::new(runtime, state, operation)))
            }
            ProxyStateV1Operation::DeregisterMiner { .. } => Ok(Box::new(
                DeregisterMinerHandler::new(runtime, state, operation),
            )),
            ProxyStateV1Operation::CreateChain { .. } => {
                Ok(Box::new(CreateChainHandler::new(runtime, state, operation)))
            }
            ProxyStateV1Operation::CreateChainToken { .. } => Ok(Box::new(
                CreateChainTokenHandler::new(runtime, state, operation),
            )),
            ProxyStateV1Operation::MemeBytecodeId { .. } => Ok(Box::new(
                MemeBytecodeIdHandler::new(runtime, state, operation),
            )),
            ProxyStateV1Operation::MemeStateBytecodeIds { .. } => Ok(Box::new(
                MemeStateBytecodeIdsHandler::new(runtime, state, operation),
            )),
            ProxyStateV1Operation::SwapApplicationId { .. } => Ok(Box::new(
                SwapApplicationIdHandler::new(runtime, state, operation),
            )),
            ProxyStateV1Operation::IsGenesisMiner { .. } => Ok(Box::new(
                IsGenesisMinerHandler::new(runtime, state, operation),
            )),
            ProxyStateV1Operation::Miners { .. } => {
                Ok(Box::new(MinersHandler::new(runtime, state, operation)))
            }
            ProxyStateV1Operation::MinerOwners { .. } => {
                Ok(Box::new(MinerOwnersHandler::new(runtime, state, operation)))
            }
            ProxyStateV1Operation::GenesisMiners { .. } => {
                Ok(Box::new(GenesisMinersHandler::new(runtime, state, operation)))
            }
            ProxyStateV1Operation::Chain { .. } => {
                Ok(Box::new(ChainHandler::new(runtime, state, operation)))
            }
            ProxyStateV1Operation::Chains { .. } => {
                Ok(Box::new(ChainsHandler::new(runtime, state, operation)))
            }
            ProxyStateV1Operation::ChainByToken { .. } => Ok(Box::new(
                ChainByTokenHandler::new(runtime, state, operation),
            )),
            ProxyStateV1Operation::Handoff { .. } => {
                Ok(Box::new(HandoffHandler::new(runtime, state, operation)))
            }
            ProxyStateV1Operation::SetOperator { .. } => Ok(Box::new(
                SetOperatorHandler::new(runtime, state, operation),
            )),
            ProxyStateV1Operation::ValidateOperator { .. } => Ok(Box::new(
                ValidateOperatorHandler::new(runtime, state, operation),
            )),
        }
    }
}
