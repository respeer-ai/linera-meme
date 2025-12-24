use std::{cell::RefCell, rc::Rc};

use super::errors::RuntimeError;
use crate::interfaces::{
    access_control::AccessControl, base::BaseRuntimeContext, contract::ContractRuntimeContext,
    meme::MemeRuntimeContext,
};
use abi::meme::{MemeAbi, MemeOperation, MemeResponse};
use linera_sdk::{
    abi::ContractAbi,
    linera_base_types::{Account, AccountOwner, ApplicationId, ChainId, ModuleId, Timestamp},
    Contract, ContractRuntime,
};
use serde::Serialize;

pub struct ContractRuntimeAdapter<T: Contract, M> {
    runtime: Rc<RefCell<ContractRuntime<T>>>,
    _message_marker: std::marker::PhantomData<M>,
}

impl<T: Contract, M> ContractRuntimeAdapter<T, M> {
    pub fn new(runtime: Rc<RefCell<ContractRuntime<T>>>) -> Self {
        Self {
            runtime,
            _message_marker: std::marker::PhantomData,
        }
    }
}

impl<T: Contract<Message = M>, M> BaseRuntimeContext for ContractRuntimeAdapter<T, M> {
    fn chain_id(&mut self) -> ChainId {
        self.runtime.borrow_mut().chain_id()
    }

    fn system_time(&mut self) -> Timestamp {
        self.runtime.borrow_mut().system_time()
    }

    fn application_creator_chain_id(&mut self) -> ChainId {
        self.runtime.borrow_mut().application_creator_chain_id()
    }
}

impl<T: Contract<Message = M>, M: Serialize> ContractRuntimeContext
    for ContractRuntimeAdapter<T, M>
{
    type Error = RuntimeError;
    type Message = M;

    fn authenticated_account(&mut self) -> Account {
        let chain_id = self.runtime.borrow_mut().chain_id();
        let owner = self
            .runtime
            .borrow_mut()
            .authenticated_signer()
            .unwrap_or(AccountOwner::CHAIN);

        Account { chain_id, owner }
    }

    fn authenticated_signer(&mut self) -> Option<AccountOwner> {
        self.runtime.borrow_mut().authenticated_signer()
    }

    fn require_authenticated_signer(&mut self) -> Result<AccountOwner, RuntimeError> {
        self.runtime
            .borrow_mut()
            .authenticated_signer()
            .ok_or(RuntimeError::InvalidAuthenticatedSigner)
    }

    fn authenticated_caller_id(&mut self) -> Option<ApplicationId> {
        self.runtime.borrow_mut().authenticated_caller_id()
    }

    fn require_authenticated_caller_id(&mut self) -> Result<ApplicationId, RuntimeError> {
        self.runtime
            .borrow_mut()
            .authenticated_caller_id()
            .ok_or(RuntimeError::InvalidAuthenticatedCaller)
    }

    fn send_message(&mut self, destination: ChainId, message: M) {
        self.runtime
            .borrow_mut()
            .prepare_message(message)
            .with_authentication()
            .send_to(destination);
    }

    fn message_origin_chain_id(&mut self) -> Option<ChainId> {
        self.runtime.borrow_mut().message_origin_chain_id()
    }

    fn require_message_origin_chain_id(&mut self) -> Result<ChainId, RuntimeError> {
        self.runtime
            .borrow_mut()
            .message_origin_chain_id()
            .ok_or(RuntimeError::InvalidMessageOriginChainId)
    }

    fn message_signer_account(&mut self) -> Account {
        let mut runtime = self.runtime.borrow_mut();

        Account {
            chain_id: runtime
                .message_origin_chain_id()
                .expect("Invalid message origin chain"),
            owner: runtime
                .authenticated_signer()
                .expect("Invalid authenticated signer"),
        }
    }

    fn create_application<Abi, Parameters, InstantiationArgument>(
        &mut self,
        module_id: ModuleId,
        parameters: &Parameters,
        argument: &InstantiationArgument,
    ) -> ApplicationId<Abi>
    where
        Abi: ContractAbi,
        Parameters: Serialize,
        InstantiationArgument: Serialize,
    {
        self.runtime
            .borrow_mut()
            .create_application(module_id, parameters, argument, vec![])
    }

    fn call_application<A: ContractAbi + Send>(
        &mut self,
        application: ApplicationId<A>,
        call: &A::Operation,
    ) -> A::Response {
        self.runtime
            .borrow_mut()
            .call_application(true, application, call)
    }
}

impl<T: Contract<Message = M>, M> AccessControl for ContractRuntimeAdapter<T, M> {
    type Error = RuntimeError;

    fn only_application_creator(&mut self) -> Result<(), RuntimeError> {
        let chain_id = self.runtime.borrow_mut().chain_id();
        let creator_chain_id = self.runtime.borrow_mut().application_creator_chain_id();

        (chain_id == creator_chain_id)
            .then_some(())
            .ok_or(RuntimeError::PermissionDenied(
                "Only allow application creator".to_string(),
            ))
    }
}

impl<T: Contract<Message = M>, M> MemeRuntimeContext for ContractRuntimeAdapter<T, M> {
    type Error = RuntimeError;

    fn token_creator_chain_id(&mut self, token: ApplicationId) -> Result<ChainId, RuntimeError> {
        let call = MemeOperation::CreatorChainId;
        let MemeResponse::ChainId(chain_id) =
            self.runtime
                .borrow_mut()
                .call_application(true, token.with_abi::<MemeAbi>(), &call)
        else {
            return Err(RuntimeError::InvalidApplicationResponse);
        };

        Ok(chain_id)
    }
}
