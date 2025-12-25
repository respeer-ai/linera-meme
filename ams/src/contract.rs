#![cfg_attr(target_arch = "wasm32", no_main)]

use abi::ams::{AmsAbi, AmsMessage, AmsOperation, InstantiationArgument};
use ams::state::AmsState;
use linera_sdk::{
    linera_base_types::WithContractAbi,
    views::{RootView, View},
    Contract, ContractRuntime,
};
use std::{cell::RefCell, rc::Rc};

pub struct AmsContract {
    state: Rc<RefCell<AmsState>>,
    runtime: Rc<RefCell<ContractRuntime<Self>>>,
}

linera_sdk::contract!(AmsContract);

impl WithContractAbi for AmsContract {
    type Abi = AmsAbi;
}

impl Contract for AmsContract {
    type Message = AmsMessage;
    type InstantiationArgument = InstantiationArgument;
    type Parameters = ();
    type EventValue = ();

    async fn load(runtime: ContractRuntime<Self>) -> Self {
        let state = AmsState::load(runtime.root_view_storage_context())
            .await
            .expect("Failed to load state");
        AmsContract {
            state: Rc::new(RefCell::new(state)),
            runtime: Rc::new(RefCell::new(runtime)),
        }
    }

    async fn instantiate(&mut self, argument: InstantiationArgument) {
        self.runtime.borrow_mut().application_parameters();
        self._instantiate(argument);
    }

    async fn execute_operation(&mut self, operation: AmsOperation) -> Self::Response {
        self.on_op(&operation).await
    }

    async fn execute_message(&mut self, message: AmsMessage) {
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
