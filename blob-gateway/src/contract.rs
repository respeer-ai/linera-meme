#![cfg_attr(target_arch = "wasm32", no_main)]

use std::{cell::RefCell, rc::Rc};

use abi::blob_gateway::{BlobGatewayAbi, BlobGatewayMessage, BlobGatewayOperation};

use blob_gateway::state::BlobGatewayState;
use linera_sdk::{
    linera_base_types::WithContractAbi,
    views::{RootView, View},
    Contract, ContractRuntime,
};

pub struct BlobGatewayContract {
    state: Rc<RefCell<BlobGatewayState>>,
    runtime: Rc<RefCell<ContractRuntime<Self>>>,
}

linera_sdk::contract!(BlobGatewayContract);

impl WithContractAbi for BlobGatewayContract {
    type Abi = BlobGatewayAbi;
}

impl Contract for BlobGatewayContract {
    type Message = BlobGatewayMessage;
    type InstantiationArgument = ();
    type Parameters = ();
    type EventValue = ();

    async fn load(runtime: ContractRuntime<Self>) -> Self {
        let state = BlobGatewayState::load(runtime.root_view_storage_context())
            .await
            .expect("Failed to load state");
        BlobGatewayContract {
            state: Rc::new(RefCell::new(state)),
            runtime: Rc::new(RefCell::new(runtime)),
        }
    }

    async fn instantiate(&mut self, _argument: Self::InstantiationArgument) {
        self.runtime.borrow_mut().application_parameters();
    }

    async fn execute_operation(&mut self, operation: BlobGatewayOperation) -> Self::Response {
        self.on_op(&operation).await
    }

    async fn execute_message(&mut self, message: BlobGatewayMessage) {
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
