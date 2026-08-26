#![cfg_attr(target_arch = "wasm32", no_main)]

use std::{cell::RefCell, rc::Rc};

use abi::proxy::state_v1::{
    ProxyStateAbi, ProxyStateV1Operation, ProxyStateV1Response, StateInstantiationArgument,
};
use linera_sdk::{
    linera_base_types::WithContractAbi,
    views::{RootView, View},
    Contract, ContractRuntime,
};
use proxy_state::state::ProxyState;

pub struct ProxyStateContract {
    state: Rc<RefCell<ProxyState>>,
    runtime: Rc<RefCell<ContractRuntime<Self>>>,
}

linera_sdk::contract!(ProxyStateContract);

impl WithContractAbi for ProxyStateContract {
    type Abi = ProxyStateAbi;
}

impl Contract for ProxyStateContract {
    type Message = ();
    type InstantiationArgument = StateInstantiationArgument;
    type Parameters = ();
    type EventValue = ();

    async fn load(runtime: ContractRuntime<Self>) -> Self {
        let state = ProxyState::load(runtime.root_view_storage_context())
            .await
            .expect("Failed to load proxy state v1");
        Self {
            state: Rc::new(RefCell::new(state)),
            runtime: Rc::new(RefCell::new(runtime)),
        }
    }

    async fn instantiate(&mut self, argument: StateInstantiationArgument) {
        self.runtime.borrow_mut().application_parameters();
        self._instantiate(argument);
    }

    async fn execute_operation(
        &mut self,
        operation: ProxyStateV1Operation,
    ) -> ProxyStateV1Response {
        self.on_op(&operation).await
    }

    async fn execute_message(&mut self, _message: ()) {}

    async fn store(self) {
        self.state
            .borrow_mut()
            .save()
            .await
            .expect("Failed to save proxy state v1");
    }
}

mod contract_impl;

#[cfg(test)]
mod contract_tests;
