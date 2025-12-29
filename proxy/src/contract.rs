#![cfg_attr(target_arch = "wasm32", no_main)]

use std::{cell::RefCell, rc::Rc};

use abi::proxy::{InstantiationArgument, ProxyAbi, ProxyMessage, ProxyOperation};

use linera_sdk::{
    linera_base_types::WithContractAbi,
    views::{RootView, View},
    Contract, ContractRuntime,
};
use proxy::state::ProxyState;

pub struct ProxyContract {
    state: Rc<RefCell<ProxyState>>,
    runtime: Rc<RefCell<ContractRuntime<Self>>>,
}

linera_sdk::contract!(ProxyContract);

impl WithContractAbi for ProxyContract {
    type Abi = ProxyAbi;
}

impl Contract for ProxyContract {
    type Message = ProxyMessage;
    type InstantiationArgument = InstantiationArgument;
    type Parameters = ();
    type EventValue = ();

    async fn load(runtime: ContractRuntime<Self>) -> Self {
        let state = ProxyState::load(runtime.root_view_storage_context())
            .await
            .expect("Failed to load state");
        ProxyContract {
            state: Rc::new(RefCell::new(state)),
            runtime: Rc::new(RefCell::new(runtime)),
        }
    }

    async fn instantiate(&mut self, argument: InstantiationArgument) {
        self.runtime.borrow_mut().application_parameters();
        self._instantiate(argument).await;
    }

    async fn execute_operation(&mut self, operation: ProxyOperation) -> Self::Response {
        self.on_op(&operation).await
    }

    async fn execute_message(&mut self, message: ProxyMessage) {
        self.on_message(&message).await
    }

    async fn store(self) {
        self.state
            .borrow_mut()
            .save()
            .await
            .expect("Failed to save state");
    }
}

mod contract_impl;

#[cfg(test)]
mod contract_tests;
