use std::{cell::RefCell, rc::Rc};

use crate::{interfaces::state::StateInterface, state::PoolState};
use abi::{
    application_state_base::{LocalStateInterface, PublicStateBaseInterface},
    pool::state_v1::{PoolStateAbi as PoolStateV1Abi, PoolStateV1Operation, PoolStateV1Response},
    pool::{Pool, Transaction},
};
use async_trait::async_trait;
use linera_sdk::{
    linera_base_types::{Account, Amount, ApplicationId},
    util::BlockingWait,
};
use runtime::interfaces::contract::ContractRuntimeContext;

use super::StateError;

pub struct ContractStateAdapter<R: ContractRuntimeContext> {
    runtime_context: Rc<RefCell<R>>,
    state: Rc<RefCell<PoolState>>,
}

impl<R: ContractRuntimeContext> Clone for ContractStateAdapter<R> {
    fn clone(&self) -> Self {
        Self {
            runtime_context: self.runtime_context.clone(),
            state: self.state.clone(),
        }
    }
}

impl<R: ContractRuntimeContext> ContractStateAdapter<R> {
    pub fn new(runtime_context: Rc<RefCell<R>>, state: Rc<RefCell<PoolState>>) -> Self {
        Self {
            runtime_context,
            state,
        }
    }

    fn state_application_id(&self) -> Result<ApplicationId, StateError> {
        Ok(self
            .state
            .borrow()
            .latest_state_application()
            .blocking_wait()?)
    }

    fn call_state(
        &self,
        operation: &PoolStateV1Operation,
    ) -> Result<PoolStateV1Response, StateError> {
        let state_application_id = self.state_application_id()?;
        Ok(self
            .runtime_context
            .borrow()
            .call_application(state_application_id.with_abi::<PoolStateV1Abi>(), operation))
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext> PublicStateBaseInterface for ContractStateAdapter<R> {
    type Error = StateError;

    async fn append_state(
        &mut self,
        state_application_id: ApplicationId,
    ) -> Result<(), Self::Error> {
        self.state
            .borrow_mut()
            .append_state(state_application_id)
            .await
    }

    async fn handoff(
        &mut self,
        new_business_application_id: ApplicationId,
    ) -> Result<(), Self::Error> {
        let state_applications = self.state.borrow()._state_applications().await?;
        if state_applications.is_empty() {
            return Err(StateError::InvalidStateVersion);
        }
        for (version, state_application_id) in state_applications {
            let response = match version {
                1 => self.runtime_context.borrow_mut().call_application(
                    state_application_id.with_abi::<PoolStateV1Abi>(),
                    &PoolStateV1Operation::Handoff {
                        new_business_application_id,
                    },
                ),
                _ => return Err(StateError::InvalidStateVersion),
            };
            match response {
                PoolStateV1Response::Ok => {}
                _ => return Err(StateError::InvalidStateResponse),
            }
        }
        Ok(())
    }

    async fn set_operator(&mut self, new_operator: Account) -> Result<(), Self::Error> {
        match self.call_state(&PoolStateV1Operation::SetOperator { new_operator })? {
            PoolStateV1Response::Ok => Ok(()),
            _ => Err(StateError::InvalidStateResponse),
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext> StateInterface for ContractStateAdapter<R> {
    type Error = StateError;

    async fn initialize(
        &mut self,
        pool: Pool,
        router_application_id: ApplicationId,
    ) -> Result<(), Self::Error> {
        match self.call_state(&PoolStateV1Operation::Initialize {
            pool,
            router_application_id,
        })? {
            PoolStateV1Response::Ok => Ok(()),
            _ => Err(StateError::InvalidStateResponse),
        }
    }

    async fn set_fee_to(
        &mut self,
        operator: Account,
        account: Account,
    ) -> Result<(), Self::Error> {
        match self.call_state(&PoolStateV1Operation::SetFeeTo {
            operator,
            account,
        })? {
            PoolStateV1Response::Ok => Ok(()),
            _ => Err(StateError::InvalidStateResponse),
        }
    }

    async fn set_fee_to_setter(
        &mut self,
        operator: Account,
        account: Account,
    ) -> Result<(), Self::Error> {
        match self.call_state(&PoolStateV1Operation::SetFeeToSetter {
            operator,
            account,
        })? {
            PoolStateV1Response::Ok => Ok(()),
            _ => Err(StateError::InvalidStateResponse),
        }
    }

    async fn pool(&self) -> Result<Pool, Self::Error> {
        match self.call_state(&PoolStateV1Operation::Pool)? {
            PoolStateV1Response::Pool(pool) => Ok(pool),
            _ => Err(StateError::InvalidStateResponse),
        }
    }

    async fn router_application_id(&self) -> Result<ApplicationId, Self::Error> {
        match self.call_state(&PoolStateV1Operation::RouterApplicationId)? {
            PoolStateV1Response::RouterApplicationId(application_id) => Ok(application_id),
            _ => Err(StateError::InvalidStateResponse),
        }
    }

    async fn claim(
        &mut self,
        token: Option<ApplicationId>,
        owner: Account,
        amount: Amount,
    ) -> Result<(), Self::Error> {
        match self.call_state(&PoolStateV1Operation::Claim {
            token,
            owner,
            amount,
        })? {
            PoolStateV1Response::Ok => Ok(()),
            _ => Err(StateError::InvalidStateResponse),
        }
    }

    async fn claim_success(
        &mut self,
        token: Option<ApplicationId>,
        owner: Account,
        amount: Amount,
    ) -> Result<(), Self::Error> {
        match self.call_state(&PoolStateV1Operation::ClaimSuccess {
            token,
            owner,
            amount,
        })? {
            PoolStateV1Response::Ok => Ok(()),
            _ => Err(StateError::InvalidStateResponse),
        }
    }

    async fn claim_fail(
        &mut self,
        token: Option<ApplicationId>,
        owner: Account,
        amount: Amount,
    ) -> Result<(), Self::Error> {
        match self.call_state(&PoolStateV1Operation::ClaimFail {
            token,
            owner,
            amount,
        })? {
            PoolStateV1Response::Ok => Ok(()),
            _ => Err(StateError::InvalidStateResponse),
        }
    }

    async fn credit_claimable(
        &mut self,
        token: Option<ApplicationId>,
        owner: Account,
        amount: Amount,
    ) -> Result<(), Self::Error> {
        match self.call_state(&PoolStateV1Operation::CreditClaimable {
            token,
            owner,
            amount,
        })? {
            PoolStateV1Response::Ok => Ok(()),
            _ => Err(StateError::InvalidStateResponse),
        }
    }

    async fn total_supply(&self) -> Result<Amount, Self::Error> {
        match self.call_state(&PoolStateV1Operation::TotalSupply)? {
            PoolStateV1Response::TotalSupply(amount) => Ok(amount),
            _ => Err(StateError::InvalidStateResponse),
        }
    }

    async fn mint_shares(&mut self, to: Account, amount: Amount) -> Result<(), Self::Error> {
        match self.call_state(&PoolStateV1Operation::MintShares { to, amount })? {
            PoolStateV1Response::Ok => Ok(()),
            _ => Err(StateError::InvalidStateResponse),
        }
    }

    async fn burn_shares(&mut self, from: Account, amount: Amount) -> Result<(), Self::Error> {
        match self.call_state(&PoolStateV1Operation::BurnShares { from, amount })? {
            PoolStateV1Response::Ok => Ok(()),
            _ => Err(StateError::InvalidStateResponse),
        }
    }

    async fn set_pool(&mut self, pool: Pool) -> Result<(), Self::Error> {
        match self.call_state(&PoolStateV1Operation::SetPool { pool })? {
            PoolStateV1Response::Ok => Ok(()),
            _ => Err(StateError::InvalidStateResponse),
        }
    }

    async fn build_transaction(
        &mut self,
        transaction: Transaction,
    ) -> Result<Transaction, Self::Error> {
        match self.call_state(&PoolStateV1Operation::BuildTransaction { transaction })? {
            PoolStateV1Response::Transaction(transaction) => Ok(transaction),
            _ => Err(StateError::InvalidStateResponse),
        }
    }
}
