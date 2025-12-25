#![cfg_attr(target_arch = "wasm32", no_main)]

use std::{cell::RefCell, rc::Rc};

use abi::swap::router::{
    InstantiationArgument, SwapAbi, SwapMessage, SwapOperation, SwapParameters,
};

use linera_sdk::{
    linera_base_types::WithContractAbi,
    views::{RootView, View},
    Contract, ContractRuntime,
};
use swap::state::SwapState;

pub struct SwapContract {
    state: Rc<RefCell<SwapState>>,
    runtime: Rc<RefCell<ContractRuntime<Self>>>,
}

linera_sdk::contract!(SwapContract);

impl WithContractAbi for SwapContract {
    type Abi = SwapAbi;
}

impl Contract for SwapContract {
    type Message = SwapMessage;
    type InstantiationArgument = InstantiationArgument;
    type Parameters = SwapParameters;
    type EventValue = ();

    async fn load(runtime: ContractRuntime<Self>) -> Self {
        let state = SwapState::load(runtime.root_view_storage_context())
            .await
            .expect("Failed to load state");
        SwapContract {
            state: Rc::new(RefCell::new(state)),
            runtime: Rc::new(RefCell::new(runtime)),
        }
    }

    async fn instantiate(&mut self, argument: InstantiationArgument) {
        self.runtime.borrow_mut().application_parameters();
        self._instantiate(argument);
    }

    async fn execute_operation(&mut self, operation: SwapOperation) -> Self::Response {
        self.on_op(&operation).await
    }

    async fn execute_message(&mut self, message: SwapMessage) {
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
