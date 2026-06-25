#![cfg_attr(target_arch = "wasm32", no_main)]

use abi::state::{StateAbi, StateMessage, StateOperation};
use linera_sdk::{
    linera_base_types::WithContractAbi,
    views::{RootView, View},
    Contract, ContractRuntime,
};
use state::state::State;
use std::{cell::RefCell, rc::Rc};

pub struct StateContract {
    state: Rc<RefCell<State>>,
    runtime: Rc<RefCell<ContractRuntime<Self>>>,
}

linera_sdk::contract!(StateContract);

impl WithContractAbi for StateContract {
    type Abi = StateAbi;
}

impl Contract for StateContract {
    type Message = StateMessage;
    type InstantiationArgument = ();
    type Parameters = ();
    type EventValue = ();

    async fn load(runtime: ContractRuntime<Self>) -> Self {
        let state = State::load(runtime.root_view_storage_context())
            .await
            .expect("Failed to load state");
        StateContract {
            state: Rc::new(RefCell::new(state)),
            runtime: Rc::new(RefCell::new(runtime)),
        }
    }

    async fn instantiate(&mut self, _argument: ()) {
        self.runtime.borrow_mut().application_parameters();
    }

    async fn execute_operation(&mut self, operation: StateOperation) -> Self::Response {
        self.on_op(&operation).await
    }

    async fn execute_message(&mut self, message: StateMessage) {
        self.on_message(&message).await;
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
