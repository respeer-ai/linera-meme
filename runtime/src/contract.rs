use std::{cell::RefCell, rc::Rc};

use super::errors::RuntimeError;
use crate::interfaces::{
    access_control::AccessControl, base::BaseRuntimeContext, contract::ContractRuntimeContext,
};
use linera_sdk::{
    linera_base_types::{Account, AccountOwner, ChainId, Timestamp},
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
        Account {
            chain_id: self.runtime.borrow_mut().chain_id(),
            owner: self
                .runtime
                .borrow_mut()
                .authenticated_signer()
                .unwrap_or(AccountOwner::CHAIN),
        }
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
