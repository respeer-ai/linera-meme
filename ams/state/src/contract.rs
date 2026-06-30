#![cfg_attr(target_arch = "wasm32", no_main)]

use std::{cell::RefCell, rc::Rc};

use abi::ams::state_v1::{
    AmsStateAbi, AmsStateOperation, AmsStateResponse, StateInstantiationArgument,
};
use ams_state::state::AmsState;
use linera_sdk::{
    linera_base_types::WithContractAbi,
    views::{RootView, View},
    Contract, ContractRuntime,
};

pub struct AmsStateContract {
    state: Rc<RefCell<AmsState>>,
    runtime: Rc<RefCell<ContractRuntime<Self>>>,
}

linera_sdk::contract!(AmsStateContract);

impl WithContractAbi for AmsStateContract {
    type Abi = AmsStateAbi;
}

impl Contract for AmsStateContract {
    type Message = ();
    type InstantiationArgument = StateInstantiationArgument;
    type Parameters = ();
    type EventValue = ();

    async fn load(runtime: ContractRuntime<Self>) -> Self {
        let state = AmsState::load(runtime.root_view_storage_context())
            .await
            .expect("Failed to load AMS StateV1 state");
        Self {
            state: Rc::new(RefCell::new(state)),
            runtime: Rc::new(RefCell::new(runtime)),
        }
    }

    async fn instantiate(&mut self, argument: StateInstantiationArgument) {
        self.runtime.borrow_mut().application_parameters();
        self._instantiate(argument);
    }

    async fn execute_operation(&mut self, operation: AmsStateOperation) -> AmsStateResponse {
        self.on_op(&operation).await
    }

    async fn execute_message(&mut self, _message: ()) {}

    async fn store(self) {
        self.state
            .borrow_mut()
            .save()
            .await
            .expect("Failed to save AMS StateV1 state");
    }
}

mod contract_impl;

#[cfg(test)]
mod contract_tests;
