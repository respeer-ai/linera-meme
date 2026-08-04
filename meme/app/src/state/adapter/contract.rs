use std::{cell::RefCell, rc::Rc};

use crate::{interfaces::state::StateInterface, state::MemeState};
use abi::{
    application_state_base::{LocalStateInterface, PublicStateBaseInterface},
    meme::{
        state_v1::{MemeStateAbi as MemeStateV1Abi, MemeStateV1Operation, MemeStateV1Response},
        HandoffArgument, InitializeArgument, Liquidity, MiningInfo,
    },
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
    state: Rc<RefCell<MemeState>>,
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
    pub fn new(runtime_context: Rc<RefCell<R>>, state: Rc<RefCell<MemeState>>) -> Self {
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
        &mut self,
        operation: &MemeStateV1Operation,
    ) -> Result<MemeStateV1Response, StateError> {
        let state_application_id = self.state_application_id()?;
        Ok(self
            .runtime_context
            .borrow_mut()
            .call_application(state_application_id.with_abi::<MemeStateV1Abi>(), operation))
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
        StateInterface::handoff(
            self,
            HandoffArgument {
                new_business_application_id,
                new_proxy_application_id: None,
                new_swap_application_id: None,
                new_ams_application_id: None,
                new_blob_gateway_application_id: None,
            },
        )
        .await
    }

    async fn set_operator(&mut self, _new_operator: Account) -> Result<(), Self::Error> {
        // TODO: forward operator update to the state app once SetOperator is added there.
        Ok(())
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext> StateInterface for ContractStateAdapter<R> {
    type Error = StateError;

    async fn owner(&self) -> Result<Account, Self::Error> {
        match self.runtime_context.borrow_mut().call_application(
            self.state_application_id()?.with_abi::<MemeStateV1Abi>(),
            &MemeStateV1Operation::Owner,
        ) {
            MemeStateV1Response::Owner(owner) => Ok(owner),
            MemeStateV1Response::Fail(error) => Err(StateError::StateOperationFailed(error)),
            _ => Err(StateError::InvalidStateResponse),
        }
    }

    async fn transfer(
        &mut self,
        origin: Account,
        to: Account,
        amount: Amount,
    ) -> Result<(), Self::Error> {
        match self.call_state(&MemeStateV1Operation::Transfer {
            from: origin,
            to,
            amount,
        })? {
            MemeStateV1Response::Ok => Ok(()),
            MemeStateV1Response::Fail(error) => Err(StateError::StateOperationFailed(error)),
            _ => Err(StateError::InvalidStateResponse),
        }
    }

    async fn transfer_from(
        &mut self,
        origin: Account,
        from: Account,
        to: Account,
        amount: Amount,
    ) -> Result<(), Self::Error> {
        match self.call_state(&MemeStateV1Operation::TransferFrom {
            origin,
            from,
            to,
            amount,
        })? {
            MemeStateV1Response::Ok => Ok(()),
            MemeStateV1Response::Fail(error) => Err(StateError::StateOperationFailed(error)),
            _ => Err(StateError::InvalidStateResponse),
        }
    }

    async fn approve(
        &mut self,
        origin: Account,
        spender: Account,
        amount: Amount,
    ) -> Result<(), Self::Error> {
        match self.call_state(&MemeStateV1Operation::Approve {
            origin,
            spender,
            amount,
        })? {
            MemeStateV1Response::Ok => Ok(()),
            MemeStateV1Response::Fail(error) => Err(StateError::StateOperationFailed(error)),
            _ => Err(StateError::InvalidStateResponse),
        }
    }

    async fn mint(&mut self, to: Account, amount: Amount) -> Result<(), Self::Error> {
        match self.call_state(&MemeStateV1Operation::Mint { to, amount })? {
            MemeStateV1Response::Ok => Ok(()),
            MemeStateV1Response::Fail(error) => Err(StateError::StateOperationFailed(error)),
            _ => Err(StateError::InvalidStateResponse),
        }
    }

    async fn transfer_ownership(
        &mut self,
        owner: Account,
        new_owner: Account,
    ) -> Result<(), Self::Error> {
        match self.call_state(&MemeStateV1Operation::TransferOwnership { owner, new_owner })? {
            MemeStateV1Response::Ok => Ok(()),
            MemeStateV1Response::Fail(error) => Err(StateError::StateOperationFailed(error)),
            _ => Err(StateError::InvalidStateResponse),
        }
    }

    async fn mining_info(&self) -> Result<MiningInfo, Self::Error> {
        match self.runtime_context.borrow_mut().call_application(
            self.state_application_id()?.with_abi::<MemeStateV1Abi>(),
            &MemeStateV1Operation::MiningInfo,
        ) {
            MemeStateV1Response::MiningInfo(info) => Ok(info),
            MemeStateV1Response::Fail(error) => Err(StateError::StateOperationFailed(error)),
            _ => Err(StateError::InvalidStateResponse),
        }
    }

    async fn redeem(
        &mut self,
        from: Account,
        to: Account,
        amount: Option<Amount>,
    ) -> Result<(), Self::Error> {
        match self.call_state(&MemeStateV1Operation::Redeem { from, to, amount })? {
            MemeStateV1Response::Ok => Ok(()),
            MemeStateV1Response::Fail(error) => Err(StateError::StateOperationFailed(error)),
            _ => Err(StateError::InvalidStateResponse),
        }
    }

    async fn transfer_from_application(
        &mut self,
        from: Account,
        to: Account,
        amount: Amount,
    ) -> Result<(), Self::Error> {
        match self.call_state(&MemeStateV1Operation::TransferFromApplication {
            from,
            to,
            amount,
        })? {
            MemeStateV1Response::Ok => Ok(()),
            MemeStateV1Response::Fail(error) => Err(StateError::StateOperationFailed(error)),
            _ => Err(StateError::InvalidStateResponse),
        }
    }

    async fn mining_reward(
        &mut self,
        owner: Account,
        reward_amount: Amount,
        mining_info: MiningInfo,
    ) -> Result<(), Self::Error> {
        match self.call_state(&MemeStateV1Operation::MiningReward {
            owner,
            reward_amount,
            mining_info,
        })? {
            MemeStateV1Response::Ok => Ok(()),
            MemeStateV1Response::Fail(error) => Err(StateError::StateOperationFailed(error)),
            _ => Err(StateError::InvalidStateResponse),
        }
    }

    async fn balance_of(&self, owner: Account) -> Result<Amount, Self::Error> {
        match self.runtime_context.borrow_mut().call_application(
            self.state_application_id()?.with_abi::<MemeStateV1Abi>(),
            &MemeStateV1Operation::Balance { owner },
        ) {
            MemeStateV1Response::Balance(amount) => Ok(amount),
            MemeStateV1Response::Fail(error) => Err(StateError::StateOperationFailed(error)),
            _ => Err(StateError::InvalidStateResponse),
        }
    }

    async fn allowance_of(&self, owner: Account, spender: Account) -> Result<Amount, Self::Error> {
        match self.runtime_context.borrow_mut().call_application(
            self.state_application_id()?.with_abi::<MemeStateV1Abi>(),
            &MemeStateV1Operation::Allowance { owner, spender },
        ) {
            MemeStateV1Response::Allowance(amount) => Ok(amount),
            MemeStateV1Response::Fail(error) => Err(StateError::StateOperationFailed(error)),
            _ => Err(StateError::InvalidStateResponse),
        }
    }

    async fn swap_application_id(&self) -> Result<Option<ApplicationId>, Self::Error> {
        match self.runtime_context.borrow_mut().call_application(
            self.state_application_id()?.with_abi::<MemeStateV1Abi>(),
            &MemeStateV1Operation::SwapApplicationId,
        ) {
            MemeStateV1Response::SwapApplicationId(application_id) => Ok(application_id),
            MemeStateV1Response::Fail(error) => Err(StateError::StateOperationFailed(error)),
            _ => Err(StateError::InvalidStateResponse),
        }
    }

    async fn proxy_application_id(&self) -> Result<Option<ApplicationId>, Self::Error> {
        match self.runtime_context.borrow_mut().call_application(
            self.state_application_id()?.with_abi::<MemeStateV1Abi>(),
            &MemeStateV1Operation::ProxyApplicationId,
        ) {
            MemeStateV1Response::ProxyApplicationId(application_id) => Ok(application_id),
            MemeStateV1Response::Fail(error) => Err(StateError::StateOperationFailed(error)),
            _ => Err(StateError::InvalidStateResponse),
        }
    }

    async fn start_mining(&mut self) -> Result<(), Self::Error> {
        match self.call_state(&MemeStateV1Operation::StartMining)? {
            MemeStateV1Response::Ok => Ok(()),
            MemeStateV1Response::Fail(error) => Err(StateError::StateOperationFailed(error)),
            _ => Err(StateError::InvalidStateResponse),
        }
    }

    async fn initialize(&mut self, argument: InitializeArgument) -> Result<(), Self::Error> {
        match self.call_state(&MemeStateV1Operation::Initialize { argument })? {
            MemeStateV1Response::Ok => Ok(()),
            MemeStateV1Response::Fail(error) => Err(StateError::StateOperationFailed(error)),
            _ => Err(StateError::InvalidStateResponse),
        }
    }

    async fn initial_liquidity(&self) -> Result<Option<Liquidity>, Self::Error> {
        match self.runtime_context.borrow_mut().call_application(
            self.state_application_id()?.with_abi::<MemeStateV1Abi>(),
            &MemeStateV1Operation::InitialLiquidity,
        ) {
            MemeStateV1Response::InitialLiquidity(liquidity) => Ok(liquidity),
            MemeStateV1Response::Fail(error) => Err(StateError::StateOperationFailed(error)),
            _ => Err(StateError::InvalidStateResponse),
        }
    }

    async fn handoff(&mut self, argument: HandoffArgument) -> Result<(), Self::Error> {
        let state_applications = self.state.borrow()._state_applications().await?;
        for (version, state_application_id) in state_applications {
            let response = match version {
                1 => self.runtime_context.borrow_mut().call_application(
                    state_application_id.with_abi::<MemeStateV1Abi>(),
                    &MemeStateV1Operation::Handoff {
                        argument: argument.clone(),
                    },
                ),
                _ => return Err(StateError::InvalidStateVersion),
            };
            match response {
                MemeStateV1Response::Ok => {}
                MemeStateV1Response::Fail(error) => {
                    return Err(StateError::StateOperationFailed(error))
                }
                _ => return Err(StateError::InvalidStateResponse),
            }
        }
        Ok(())
    }
}
