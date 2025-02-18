// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

#![cfg_attr(target_arch = "wasm32", no_main)]

mod state;

use linera_sdk::{
    base::WithContractAbi,
    views::{RootView, View},
    Contract, ContractRuntime,
};
use proxy::ProxyAbi;

use self::state::ProxyState;

pub struct ProxyContract {
    state: ProxyState,
    runtime: ContractRuntime<Self>,
}

linera_sdk::contract!(ProxyContract);

impl WithContractAbi for ProxyContract {
    type Abi = ProxyAbi;
}

impl Contract for ProxyContract {
    type Message = ();
    type InstantiationArgument = u64;
    type Parameters = ();

    async fn load(runtime: ContractRuntime<Self>) -> Self {
        let state = ProxyState::load(runtime.root_view_storage_context())
            .await
            .expect("Failed to load state");
        ProxyContract { state, runtime }
    }

    async fn instantiate(&mut self, value: u64) {
        // Validate that the application parameters were configured correctly.
        self.runtime.application_parameters();

        self.state.value.set(value);
    }

    async fn execute_operation(&mut self, operation: u64) -> u64 {
        let new_value = self.state.value.get() + operation;
        self.state.value.set(new_value);
        new_value
    }

    async fn execute_message(&mut self, _message: ()) {
        panic!("Proxy application doesn't support any cross-chain messages");
    }

    async fn store(mut self) {
        self.state.save().await.expect("Failed to save state");
    }
}

#[cfg(test)]
mod tests {
    use futures::FutureExt as _;
    use linera_sdk::{util::BlockingWait, views::View, Contract, ContractRuntime};

    use super::{ProxyContract, ProxyState};

    #[test]
    fn operation() {
        let initial_value = 72_u64;
        let mut proxy = create_and_instantiate_proxy(initial_value);

        let increment = 42_308_u64;

        let response = proxy
            .execute_operation(increment)
            .now_or_never()
            .expect("Execution of proxy operation should not await anything");

        let expected_value = initial_value + increment;

        assert_eq!(response, expected_value);
        assert_eq!(*proxy.state.value.get(), initial_value + increment);
    }

    #[test]
    #[should_panic(expected = "Proxy application doesn't support any cross-chain messages")]
    fn message() {
        let initial_value = 72_u64;
        let mut proxy = create_and_instantiate_proxy(initial_value);

        proxy
            .execute_message(())
            .now_or_never()
            .expect("Execution of proxy operation should not await anything");
    }

    #[test]
    fn cross_application_call() {
        let initial_value = 2_845_u64;
        let mut proxy = create_and_instantiate_proxy(initial_value);

        let increment = 8_u64;

        let response = proxy
            .execute_operation(increment)
            .now_or_never()
            .expect("Execution of proxy operation should not await anything");

        let expected_value = initial_value + increment;

        assert_eq!(response, expected_value);
        assert_eq!(*proxy.state.value.get(), expected_value);
    }

    fn create_and_instantiate_proxy(initial_value: u64) -> ProxyContract {
        let runtime = ContractRuntime::new().with_application_parameters(());
        let mut contract = ProxyContract {
            state: ProxyState::load(runtime.root_view_storage_context())
                .blocking_wait()
                .expect("Failed to read from mock key value store"),
            runtime,
        };

        contract
            .instantiate(initial_value)
            .now_or_never()
            .expect("Initialization of proxy state should not await anything");

        assert_eq!(*contract.state.value.get(), initial_value);

        contract
    }
}
