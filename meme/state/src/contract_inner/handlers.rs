pub mod operation;

use abi::meme::{MemeStateV1Operation, MemeStateV1Response};
use base::handler::{Handler, HandlerError};
use runtime::interfaces::{access_control::AccessControl, contract::ContractRuntimeContext};
use std::{cell::RefCell, rc::Rc};

use crate::interfaces::state::StateInterface;

use operation::allowance::AllowanceHandler;
use operation::approve::ApproveHandler;
use operation::balance::BalanceHandler;
use operation::handoff::HandoffHandler;
use operation::initialize::InitializeHandler;
use operation::mining_info::MiningInfoHandler;
use operation::mining_reward::MiningRewardHandler;
use operation::mint::MintHandler;
use operation::owner::OwnerHandler;
use operation::proxy_application_id::ProxyApplicationIdHandler;
use operation::redeem::RedeemHandler;
use operation::start_mining::StartMiningHandler;
use operation::swap_application_id::SwapApplicationIdHandler;
use operation::transfer_ownership::TransferOwnershipHandler;
use operation::transfer::TransferHandler;
use operation::transfer_from::TransferFromHandler;
use operation::transfer_from_application::TransferFromApplicationHandler;

pub struct HandlerFactory;

impl HandlerFactory {
    fn new_operation_handler(
        runtime: Rc<RefCell<impl ContractRuntimeContext<Message = ()> + AccessControl + 'static>>,
        state: impl StateInterface + 'static,
        operation: &MemeStateV1Operation,
    ) -> Result<Box<dyn Handler<(), MemeStateV1Response>>, HandlerError> {
        match operation {
            MemeStateV1Operation::Transfer { .. } => {
                Ok(Box::new(TransferHandler::new(runtime, state, operation)))
            }
            MemeStateV1Operation::TransferFrom { .. } => Ok(Box::new(TransferFromHandler::new(
                runtime, state, operation,
            ))),
            MemeStateV1Operation::Approve { .. } => {
                Ok(Box::new(ApproveHandler::new(runtime, state, operation)))
            }
            MemeStateV1Operation::Initialize { .. } => {
                Ok(Box::new(InitializeHandler::new(runtime, state, operation)))
            }
            MemeStateV1Operation::Mint { .. } => {
                Ok(Box::new(MintHandler::new(runtime, state, operation)))
            }
            MemeStateV1Operation::TransferOwnership { .. } => Ok(Box::new(
                TransferOwnershipHandler::new(runtime, state, operation),
            )),
            MemeStateV1Operation::Redeem { .. } => {
                Ok(Box::new(RedeemHandler::new(runtime, state, operation)))
            }
            MemeStateV1Operation::TransferFromApplication { .. } => Ok(Box::new(
                TransferFromApplicationHandler::new(runtime, state, operation),
            )),
            MemeStateV1Operation::MiningReward { .. } => Ok(Box::new(MiningRewardHandler::new(
                runtime, state, operation,
            ))),
            MemeStateV1Operation::MiningInfo => {
                Ok(Box::new(MiningInfoHandler::new(runtime, state, operation)))
            }
            MemeStateV1Operation::Handoff { .. } => {
                Ok(Box::new(HandoffHandler::new(runtime, state, operation)))
            }
            MemeStateV1Operation::Balance { .. } => {
                Ok(Box::new(BalanceHandler::new(runtime, state, operation)))
            }
            MemeStateV1Operation::Allowance { .. } => {
                Ok(Box::new(AllowanceHandler::new(runtime, state, operation)))
            }
            MemeStateV1Operation::Owner => {
                Ok(Box::new(OwnerHandler::new(runtime, state, operation)))
            }
            MemeStateV1Operation::SwapApplicationId => Ok(Box::new(
                SwapApplicationIdHandler::new(runtime, state, operation),
            )),
            MemeStateV1Operation::ProxyApplicationId => Ok(Box::new(
                ProxyApplicationIdHandler::new(runtime, state, operation),
            )),
            MemeStateV1Operation::StartMining => {
                Ok(Box::new(StartMiningHandler::new(runtime, state, operation)))
            }
        }
    }

    pub fn new(
        runtime: Rc<RefCell<impl ContractRuntimeContext<Message = ()> + AccessControl + 'static>>,
        state: impl StateInterface + 'static,
        operation: Option<&MemeStateV1Operation>,
        message: Option<&()>,
    ) -> Result<Box<dyn Handler<(), MemeStateV1Response>>, HandlerError> {
        if let Some(operation) = operation {
            return Self::new_operation_handler(runtime, state, operation);
        }
        if message.is_some() {
            return Err(HandlerError::NotImplemented);
        }
        Err(HandlerError::InvalidOperationAndMessage)
    }
}
