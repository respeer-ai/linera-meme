#![cfg_attr(target_arch = "wasm32", no_main)]

use std::{cell::RefCell, rc::Rc};

use abi::blob_gateway::state_v1::{
    BlobGatewayStateAbi, BlobGatewayStateV1Operation, BlobGatewayStateV1Response,
    StateInstantiationArgument,
};
use blob_gateway_state::state::BlobGatewayStateV1;
use linera_sdk::{
    linera_base_types::WithContractAbi,
    views::{RootView, View},
    Contract, ContractRuntime,
};

pub struct BlobGatewayStateContract {
    state: Rc<RefCell<BlobGatewayStateV1>>,
    runtime: Rc<RefCell<ContractRuntime<Self>>>,
}

linera_sdk::contract!(BlobGatewayStateContract);

impl WithContractAbi for BlobGatewayStateContract {
    type Abi = BlobGatewayStateAbi;
}

impl Contract for BlobGatewayStateContract {
    type Message = ();
    type InstantiationArgument = StateInstantiationArgument;
    type Parameters = ();
    type EventValue = ();

    async fn load(runtime: ContractRuntime<Self>) -> Self {
        let state = BlobGatewayStateV1::load(runtime.root_view_storage_context())
            .await
            .expect("Failed to load blob gateway StateV1 state");
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
        operation: BlobGatewayStateV1Operation,
    ) -> BlobGatewayStateV1Response {
        self.on_op(&operation).await
    }

    async fn execute_message(&mut self, _message: ()) {}

    async fn store(self) {
        self.state
            .borrow_mut()
            .save()
            .await
            .expect("Failed to save blob gateway StateV1 state");
    }
}

mod contract_impl;

#[cfg(test)]
mod contract_tests;
