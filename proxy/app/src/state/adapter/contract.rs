use std::{cell::RefCell, rc::Rc};

use crate::{interfaces::state::StateInterface, state::ProxyState};
use abi::{
    application_state_base::{LocalStateInterface, PublicStateBaseInterface},
    proxy::{
        state_v1::{
            ProxyStateAbi as ProxyStateV1Abi, ProxyStateV1Operation, ProxyStateV1Response,
        },
        InitializeArgument,
    },
};
use async_trait::async_trait;
use linera_sdk::{
    linera_base_types::{Account, AccountOwner, ApplicationId, ChainId, ModuleId, Timestamp},
    util::BlockingWait,
};
use runtime::interfaces::contract::ContractRuntimeContext;

use super::StateError;

pub struct ContractStateAdapter<R: ContractRuntimeContext> {
    runtime_context: Rc<RefCell<R>>,
    state: Rc<RefCell<ProxyState>>,
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
    pub fn new(runtime_context: Rc<RefCell<R>>, state: Rc<RefCell<ProxyState>>) -> Self {
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
        operation: &ProxyStateV1Operation,
    ) -> Result<ProxyStateV1Response, StateError> {
        let state_application_id = self.state_application_id()?;
        Ok(self
            .runtime_context
            .borrow()
            .call_application(state_application_id.with_abi::<ProxyStateV1Abi>(), operation))
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
                    state_application_id.with_abi::<ProxyStateV1Abi>(),
                    &ProxyStateV1Operation::Handoff {
                        new_business_application_id,
                    },
                ),
                _ => return Err(StateError::InvalidStateVersion),
            };
            match response {
                ProxyStateV1Response::Ok => {}
                _ => return Err(StateError::InvalidStateResponse),
            }
        }
        Ok(())
    }

    async fn set_operator(&mut self, new_operator: Account) -> Result<(), Self::Error> {
        match self.call_state(&ProxyStateV1Operation::SetOperator { new_operator })? {
            ProxyStateV1Response::Ok => Ok(()),
            _ => Err(StateError::InvalidStateResponse),
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext> StateInterface for ContractStateAdapter<R> {
    type Error = StateError;

    async fn initialize(&mut self, argument: InitializeArgument) -> Result<(), Self::Error> {
        match self.call_state(&ProxyStateV1Operation::Initialize { argument })? {
            ProxyStateV1Response::Ok => Ok(()),
            _ => Err(StateError::InvalidStateResponse),
        }
    }

    async fn add_genesis_miner(&mut self, owner: Account) -> Result<(), Self::Error> {
        match self.call_state(&ProxyStateV1Operation::AddGenesisMiner { owner })? {
            ProxyStateV1Response::Ok => Ok(()),
            _ => Err(StateError::InvalidStateResponse),
        }
    }

    async fn approve_add_genesis_miner(
        &mut self,
        owner: Account,
        operator: Account,
    ) -> Result<(), Self::Error> {
        match self.call_state(&ProxyStateV1Operation::ApproveAddGenesisMiner { owner, operator })? {
            ProxyStateV1Response::Ok => Ok(()),
            _ => Err(StateError::InvalidStateResponse),
        }
    }

    async fn remove_genesis_miner(&mut self, owner: Account) -> Result<(), Self::Error> {
        match self.call_state(&ProxyStateV1Operation::RemoveGenesisMiner { owner })? {
            ProxyStateV1Response::Ok => Ok(()),
            _ => Err(StateError::InvalidStateResponse),
        }
    }

    async fn approve_remove_genesis_miner(
        &mut self,
        owner: Account,
        operator: Account,
    ) -> Result<(), Self::Error> {
        match self
            .call_state(&ProxyStateV1Operation::ApproveRemoveGenesisMiner { owner, operator })?
        {
            ProxyStateV1Response::Ok => Ok(()),
            _ => Err(StateError::InvalidStateResponse),
        }
    }

    async fn add_operator(&mut self, owner: Account) -> Result<(), Self::Error> {
        match self.call_state(&ProxyStateV1Operation::AddOperator { owner })? {
            ProxyStateV1Response::Ok => Ok(()),
            _ => Err(StateError::InvalidStateResponse),
        }
    }

    async fn approve_add_operator(
        &mut self,
        owner: Account,
        operator: Account,
    ) -> Result<(), Self::Error> {
        match self.call_state(&ProxyStateV1Operation::ApproveAddOperator { owner, operator })? {
            ProxyStateV1Response::Ok => Ok(()),
            _ => Err(StateError::InvalidStateResponse),
        }
    }

    async fn ban_operator(&mut self, owner: Account) -> Result<(), Self::Error> {
        match self.call_state(&ProxyStateV1Operation::BanOperator { owner })? {
            ProxyStateV1Response::Ok => Ok(()),
            _ => Err(StateError::InvalidStateResponse),
        }
    }

    async fn approve_ban_operator(
        &mut self,
        owner: Account,
        operator: Account,
    ) -> Result<(), Self::Error> {
        match self.call_state(&ProxyStateV1Operation::ApproveBanOperator { owner, operator })? {
            ProxyStateV1Response::Ok => Ok(()),
            _ => Err(StateError::InvalidStateResponse),
        }
    }

    async fn set_meme_bytecode_ids(
        &mut self,
        business_bytecode_id: ModuleId,
        state_bytecode_id: ModuleId,
    ) -> Result<(), Self::Error> {
        match self.call_state(&ProxyStateV1Operation::SetMemeBytecodeIds {
            business_bytecode_id,
            state_bytecode_id,
        })? {
            ProxyStateV1Response::Ok => Ok(()),
            _ => Err(StateError::InvalidStateResponse),
        }
    }

    fn create_chain(&mut self, chain_id: ChainId, timestamp: Timestamp) -> Result<(), Self::Error> {
        match self.call_state(&ProxyStateV1Operation::CreateChain {
            chain_id,
            created_at: timestamp,
        })? {
            ProxyStateV1Response::Ok => Ok(()),
            _ => Err(StateError::InvalidStateResponse),
        }
    }

    async fn create_chain_token(
        &mut self,
        chain_id: ChainId,
        token: ApplicationId,
    ) -> Result<(), Self::Error> {
        match self.call_state(&ProxyStateV1Operation::CreateChainToken { chain_id, token })? {
            ProxyStateV1Response::Ok => Ok(()),
            _ => Err(StateError::InvalidStateResponse),
        }
    }

    async fn register_miner(
        &mut self,
        owner: Account,
        now: Timestamp,
    ) -> Result<(), Self::Error> {
        match self.call_state(&ProxyStateV1Operation::RegisterMiner { owner, now })? {
            ProxyStateV1Response::Ok => Ok(()),
            _ => Err(StateError::InvalidStateResponse),
        }
    }

    async fn deregister_miner(&mut self, owner: Account) -> Result<(), Self::Error> {
        match self.call_state(&ProxyStateV1Operation::DeregisterMiner { owner })? {
            ProxyStateV1Response::Ok => Ok(()),
            _ => Err(StateError::InvalidStateResponse),
        }
    }

    async fn genesis_miners(&self) -> Result<Vec<abi::proxy::Miner>, Self::Error> {
        match self.call_state(&ProxyStateV1Operation::GenesisMiners)? {
            ProxyStateV1Response::Miners(miners) => Ok(miners),
            _ => Err(StateError::InvalidStateResponse),
        }
    }

    async fn is_genesis_miner(&self, owner: Account) -> Result<bool, Self::Error> {
        match self.call_state(&ProxyStateV1Operation::IsGenesisMiner { owner })? {
            ProxyStateV1Response::Bool(value) => Ok(value),
            _ => Err(StateError::InvalidStateResponse),
        }
    }

    async fn genesis_miner_owners(&self) -> Result<Vec<AccountOwner>, Self::Error> {
        match self.call_state(&ProxyStateV1Operation::GenesisMiners)? {
            ProxyStateV1Response::Miners(miners) => {
                Ok(miners.into_iter().map(|miner| miner.owner.owner).collect())
            }
            _ => Err(StateError::InvalidStateResponse),
        }
    }

    async fn miners(&self) -> Result<Vec<abi::proxy::Miner>, Self::Error> {
        match self.call_state(&ProxyStateV1Operation::Miners)? {
            ProxyStateV1Response::Miners(miners) => Ok(miners),
            _ => Err(StateError::InvalidStateResponse),
        }
    }

    async fn miner_owners(&self) -> Result<Vec<AccountOwner>, Self::Error> {
        match self.call_state(&ProxyStateV1Operation::MinerOwners)? {
            ProxyStateV1Response::AccountOwners(owners) => Ok(owners),
            _ => Err(StateError::InvalidStateResponse),
        }
    }

    async fn validate_operator(&self, owner: Account) -> Result<(), Self::Error> {
        match self.call_state(&ProxyStateV1Operation::ValidateOperator { owner })? {
            ProxyStateV1Response::Ok => Ok(()),
            _ => Err(StateError::InvalidStateResponse),
        }
    }

    fn meme_bytecode_id(&self) -> ModuleId {
        match self.runtime_context.borrow_mut().call_application(
            self.state_application_id()
                .expect("Failed to get state application id")
                .with_abi::<ProxyStateV1Abi>(),
            &ProxyStateV1Operation::MemeBytecodeId,
        ) {
            ProxyStateV1Response::ModuleId(module_id) => module_id,
            _ => panic!("Invalid state response"),
        }
    }

    async fn meme_state_bytecode_ids(&self) -> Result<Vec<(u16, ModuleId)>, Self::Error> {
        match self.call_state(&ProxyStateV1Operation::MemeStateBytecodeIds)? {
            ProxyStateV1Response::ModuleIds(ids) => Ok(ids),
            _ => Err(StateError::InvalidStateResponse),
        }
    }

    fn swap_application_id(&self) -> ApplicationId {
        match self.runtime_context.borrow_mut().call_application(
            self.state_application_id()
                .expect("Failed to get state application id")
                .with_abi::<ProxyStateV1Abi>(),
            &ProxyStateV1Operation::SwapApplicationId,
        ) {
            ProxyStateV1Response::ApplicationId(application_id) => application_id,
            _ => panic!("Invalid state response"),
        }
    }
}
