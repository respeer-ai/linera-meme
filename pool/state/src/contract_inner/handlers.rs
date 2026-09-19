pub mod operation;

use abi::pool::state_v1::{PoolStateV1Operation, PoolStateV1Response};
use base::handler::{Handler, HandlerError};
use runtime::interfaces::{access_control::AccessControl, contract::ContractRuntimeContext};
use std::{cell::RefCell, rc::Rc};

use crate::interfaces::state::StateInterface;

use operation::{
    build_transaction::BuildTransactionHandler, burn_shares::BurnSharesHandler,
    claim::ClaimHandler, claim_fail::ClaimFailHandler, claim_success::ClaimSuccessHandler,
    claimable_balance::ClaimableBalanceHandler, claiming_balance::ClaimingBalanceHandler,
    credit_claimable::CreditClaimableHandler, debit_claimable::DebitClaimableHandler,
    handoff::HandoffHandler, initialize::InitializeHandler, liquidity::LiquidityHandler,
    mint_shares::MintSharesHandler, pool::PoolHandler,
    router_application_id::RouterApplicationIdHandler, set_fee_to::SetFeeToHandler,
    set_fee_to_setter::SetFeeToSetterHandler, set_operator::SetOperatorHandler,
    set_pool::SetPoolHandler, total_supply::TotalSupplyHandler,
};

pub struct HandlerFactory;

impl HandlerFactory {
    pub fn new(
        runtime: Rc<RefCell<impl ContractRuntimeContext<Message = ()> + AccessControl + 'static>>,
        state: impl StateInterface + 'static,
        operation: Option<&PoolStateV1Operation>,
        message: Option<&()>,
    ) -> Result<Box<dyn Handler<(), PoolStateV1Response>>, HandlerError> {
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
        operation: &PoolStateV1Operation,
    ) -> Result<Box<dyn Handler<(), PoolStateV1Response>>, HandlerError> {
        match operation {
            PoolStateV1Operation::BuildTransaction { .. } => Ok(Box::new(
                BuildTransactionHandler::new(runtime, state, operation),
            )),
            PoolStateV1Operation::Claim { .. } => {
                Ok(Box::new(ClaimHandler::new(runtime, state, operation)))
            }
            PoolStateV1Operation::ClaimSuccess { .. } => Ok(Box::new(
                ClaimSuccessHandler::new(runtime, state, operation),
            )),
            PoolStateV1Operation::ClaimFail { .. } => {
                Ok(Box::new(ClaimFailHandler::new(runtime, state, operation)))
            }
            PoolStateV1Operation::ClaimableBalance { .. } => Ok(Box::new(
                ClaimableBalanceHandler::new(runtime, state, operation),
            )),
            PoolStateV1Operation::ClaimingBalance { .. } => Ok(Box::new(
                ClaimingBalanceHandler::new(runtime, state, operation),
            )),
            PoolStateV1Operation::CreditClaimable { .. } => Ok(Box::new(
                CreditClaimableHandler::new(runtime, state, operation),
            )),
            PoolStateV1Operation::DebitClaimable { .. } => Ok(Box::new(
                DebitClaimableHandler::new(runtime, state, operation),
            )),
            PoolStateV1Operation::BurnShares { .. } => Ok(Box::new(BurnSharesHandler::new(
                runtime, state, operation,
            ))),
            PoolStateV1Operation::Initialize { .. } => Ok(Box::new(InitializeHandler::new(
                runtime, state, operation,
            ))),
            PoolStateV1Operation::Liquidity { .. } => {
                Ok(Box::new(LiquidityHandler::new(runtime, state, operation)))
            }
            PoolStateV1Operation::MintShares { .. } => Ok(Box::new(MintSharesHandler::new(
                runtime, state, operation,
            ))),
            PoolStateV1Operation::Pool => {
                Ok(Box::new(PoolHandler::new(runtime, state, operation)))
            }
            PoolStateV1Operation::RouterApplicationId => Ok(Box::new(
                RouterApplicationIdHandler::new(runtime, state, operation),
            )),
            PoolStateV1Operation::SetFeeTo { .. } => {
                Ok(Box::new(SetFeeToHandler::new(runtime, state, operation)))
            }
            PoolStateV1Operation::SetFeeToSetter { .. } => Ok(Box::new(
                SetFeeToSetterHandler::new(runtime, state, operation),
            )),
            PoolStateV1Operation::SetOperator { .. } => Ok(Box::new(SetOperatorHandler::new(
                runtime, state, operation,
            ))),
            PoolStateV1Operation::SetPool { .. } => {
                Ok(Box::new(SetPoolHandler::new(runtime, state, operation)))
            }
            PoolStateV1Operation::TotalSupply => {
                Ok(Box::new(TotalSupplyHandler::new(runtime, state, operation)))
            }
            PoolStateV1Operation::Handoff { .. } => {
                Ok(Box::new(HandoffHandler::new(runtime, state, operation)))
            }
        }
    }
}
