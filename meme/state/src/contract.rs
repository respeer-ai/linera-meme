#![cfg_attr(target_arch = "wasm32", no_main)]

use std::{cell::RefCell, rc::Rc};

use abi::meme::{
    MemeStateAbi, MemeStateV1Operation, MemeStateV1Response, StateInstantiationArgument,
};
use linera_sdk::{
    linera_base_types::WithContractAbi,
    views::{RootView, View},
    Contract, ContractRuntime,
};
use meme_state::state::MemeState;

pub struct MemeStateContract {
    state: Rc<RefCell<MemeState>>,
    runtime: Rc<RefCell<ContractRuntime<Self>>>,
}

linera_sdk::contract!(MemeStateContract);

impl WithContractAbi for MemeStateContract {
    type Abi = MemeStateAbi;
}

impl Contract for MemeStateContract {
    type Message = ();
    type InstantiationArgument = StateInstantiationArgument;
    type Parameters = ();
    type EventValue = ();

    async fn load(runtime: ContractRuntime<Self>) -> Self {
        let state = MemeState::load(runtime.root_view_storage_context())
            .await
            .expect("Failed to load meme state v1");
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
        operation: MemeStateV1Operation,
    ) -> MemeStateV1Response {
        self.on_op(&operation).await
    }

    async fn execute_message(&mut self, _message: ()) {}

    async fn store(self) {
        self.state
            .borrow_mut()
            .save()
            .await
            .expect("Failed to save meme state v1");
    }
}

mod contract_impl;

#[cfg(test)]
mod contract_tests;
