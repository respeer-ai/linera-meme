// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

#![cfg_attr(target_arch = "wasm32", no_main)]

mod state;

use linera_sdk::{
    base::WithContractAbi,
    views::{RootView, View},
    Contract, ContractRuntime,
};
use meme::{MemeAbi, MemeOperation, MemeResponse};
use abi::meme::InstantiationArgument;

use self::state::MemeState;

pub struct MemeContract {
    state: MemeState,
    runtime: ContractRuntime<Self>,
}

linera_sdk::contract!(MemeContract);

impl WithContractAbi for MemeContract {
    type Abi = MemeAbi;
}

impl Contract for MemeContract {
    type Message = ();
    type InstantiationArgument = InstantiationArgument;
    type Parameters = ();

    async fn load(runtime: ContractRuntime<Self>) -> Self {
        let state = MemeState::load(runtime.root_view_storage_context())
            .await
            .expect("Failed to load state");
        MemeContract { state, runtime }
    }

    async fn instantiate(&mut self, instantiation_argument: InstantiationArgument) {
        // Validate that the application parameters were configured correctly.
        self.runtime.application_parameters();

        self.state.instantiate(instantiation_argument).await;
    }

    async fn execute_operation(&mut self, operation: MemeOperation) -> MemeResponse {
        MemeResponse::Ok
    }

    async fn execute_message(&mut self, _message: ()) {
        panic!("Meme application doesn't support any cross-chain messages");
    }

    async fn store(mut self) {
        self.state.save().await.expect("Failed to save state");
    }
}

#[cfg(test)]
mod tests {
    use futures::FutureExt as _;
    use linera_sdk::{util::BlockingWait, views::View, Contract, ContractRuntime};

    use super::{MemeContract, MemeState};

    #[test]
    fn operation() {
        let initial_value = 72_u64;
        let mut counter = create_and_instantiate_counter(initial_value);

        let increment = 42_308_u64;

        let response = counter
            .execute_operation(increment)
            .now_or_never()
            .expect("Execution of counter operation should not await anything");

        let expected_value = initial_value + increment;

        assert_eq!(response, expected_value);
        assert_eq!(*counter.state.value.get(), initial_value + increment);
    }

    #[test]
    #[should_panic(expected = "Meme application doesn't support any cross-chain messages")]
    fn message() {
        let initial_value = 72_u64;
        let mut counter = create_and_instantiate_counter(initial_value);

        counter
            .execute_message(())
            .now_or_never()
            .expect("Execution of counter operation should not await anything");
    }

    #[test]
    fn cross_application_call() {
        let initial_value = 2_845_u64;
        let mut counter = create_and_instantiate_counter(initial_value);

        let increment = 8_u64;

        let response = counter
            .execute_operation(increment)
            .now_or_never()
            .expect("Execution of counter operation should not await anything");

        let expected_value = initial_value + increment;

        assert_eq!(response, expected_value);
        assert_eq!(*counter.state.value.get(), expected_value);
    }

    fn create_and_instantiate_counter(initial_value: u64) -> MemeContract {
        let runtime = ContractRuntime::new().with_application_parameters(());
        let mut contract = MemeContract {
            state: MemeState::load(runtime.root_view_storage_context())
                .blocking_wait()
                .expect("Failed to read from mock key value store"),
            runtime,
        };

        contract
            .instantiate(initial_value)
            .now_or_never()
            .expect("Initialization of counter state should not await anything");

        assert_eq!(*contract.state.value.get(), initial_value);

        contract
    }
}
