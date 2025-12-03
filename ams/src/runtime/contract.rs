use std::{cell::RefCell, rc::Rc};

use super::errors::RuntimeError;
use crate::{
    abi::Message,
    interfaces::{
        access_control::AccessControl,
        runtime::{base::BaseRuntimeContext, contract::ContractRuntimeContext},
    },
};
use linera_sdk::{
    linera_base_types::{AccountOwner, ChainId, Timestamp},
    Contract, ContractRuntime,
};

pub struct ContractRuntimeAdapter<T: Contract> {
    runtime: Rc<RefCell<ContractRuntime<T>>>,
}

impl<T: Contract> ContractRuntimeAdapter<T> {
    pub fn new(runtime: Rc<RefCell<ContractRuntime<T>>>) -> Self {
        Self { runtime }
    }
}

impl<T: Contract<Message = Message>> BaseRuntimeContext for ContractRuntimeAdapter<T> {
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

impl<T: Contract<Message = Message>> ContractRuntimeContext for ContractRuntimeAdapter<T> {
    type Error = RuntimeError;

    fn authenticated_signer(&mut self) -> Option<AccountOwner> {
        self.runtime.borrow_mut().authenticated_signer()
    }

    fn require_authenticated_signer(&mut self) -> Result<AccountOwner, RuntimeError> {
        self.runtime
            .borrow_mut()
            .authenticated_signer()
            .ok_or(RuntimeError::InvalidAuthenticatedSigner)
    }

    fn send_message(&mut self, destination: ChainId, message: Message) {
        self.runtime.borrow_mut().send_message(destination, message)
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

impl<T: Contract<Message = Message>> AccessControl for ContractRuntimeAdapter<T> {
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
