#![cfg_attr(target_arch = "wasm32", no_main)]

use abi::meme::MemeAbi;
use linera_sdk::{
    linera_base_types::WithContractAbi,
    views::{RootView, View},
    Contract, ContractRuntime,
};
use meme_app::state::MemeState;
use std::{cell::RefCell, rc::Rc};

pub struct MemeContract {
    state: Rc<RefCell<MemeState>>,
    runtime: Rc<RefCell<ContractRuntime<Self>>>,
}

linera_sdk::contract!(MemeContract);

impl WithContractAbi for MemeContract {
    type Abi = MemeAbi;
}

impl Contract for MemeContract {
    type Message = abi::meme::MemeMessage;
    type Parameters = abi::meme::MemeParameters;
    type InstantiationArgument = abi::meme::InstantiationArgument;
    type EventValue = ();

    async fn load(runtime: ContractRuntime<Self>) -> Self {
        let state = MemeState::load(runtime.root_view_storage_context())
            .await
            .expect("Failed to load meme business state");
        Self {
            state: Rc::new(RefCell::new(state)),
            runtime: Rc::new(RefCell::new(runtime)),
        }
    }

    async fn instantiate(&mut self, _argument: Self::InstantiationArgument) {
        self.runtime.borrow_mut().application_parameters();
    }

    async fn execute_operation(&mut self, operation: Self::Operation) -> Self::Response {
        self.on_op(&operation).await
    }

    async fn execute_message(&mut self, message: Self::Message) {
        self.on_message(&message).await
    }

    async fn store(self) {
        self.state
            .borrow_mut()
            .save()
            .await
            .expect("Failed to save meme business state");
    }
}

mod contract_impl;
