#![cfg_attr(target_arch = "wasm32", no_main)]

use std::{cell::RefCell, rc::Rc};

use abi::pool::state_v1::{
    PoolStateAbi, PoolStateV1Operation, PoolStateV1Response, StateInstantiationArgument,
};
use linera_sdk::{
    linera_base_types::WithContractAbi,
    views::{RootView, View},
    Contract, ContractRuntime,
};
use pool_state::state::PoolState;

pub struct PoolStateContract {
    state: Rc<RefCell<PoolState>>,
    runtime: Rc<RefCell<ContractRuntime<Self>>>,
}

linera_sdk::contract!(PoolStateContract);

impl WithContractAbi for PoolStateContract {
    type Abi = PoolStateAbi;
}

impl Contract for PoolStateContract {
    type Message = ();
    type InstantiationArgument = StateInstantiationArgument;
    type Parameters = ();
    type EventValue = ();

    async fn load(runtime: ContractRuntime<Self>) -> Self {
        let state = PoolState::load(runtime.root_view_storage_context())
            .await
            .expect("Failed to load pool state v1");
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
        operation: PoolStateV1Operation,
    ) -> PoolStateV1Response {
        self.on_op(&operation).await
    }

    async fn execute_message(&mut self, _message: ()) {}

    async fn store(self) {
        self.state
            .borrow_mut()
            .save()
            .await
            .expect("Failed to save pool state v1");
    }
}

mod contract_impl;

#[cfg(test)]
mod contract_tests;
