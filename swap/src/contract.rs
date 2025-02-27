// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

#![cfg_attr(target_arch = "wasm32", no_main)]

mod state;

use abi::swap::{SwapAbi, SwapOperation, SwapResponse};
use linera_sdk::{
    base::WithContractAbi,
    views::{RootView, View},
    Contract, ContractRuntime,
};

use self::state::SwapState;

pub struct SwapContract {
    state: SwapState,
    runtime: ContractRuntime<Self>,
}

linera_sdk::contract!(SwapContract);

impl WithContractAbi for SwapContract {
    type Abi = SwapAbi;
}

impl Contract for SwapContract {
    type Message = ();
    type InstantiationArgument = ();
    type Parameters = ();

    async fn load(runtime: ContractRuntime<Self>) -> Self {
        let state = SwapState::load(runtime.root_view_storage_context())
            .await
            .expect("Failed to load state");
        SwapContract { state, runtime }
    }

    async fn instantiate(&mut self, value: ()) {
        // Validate that the application parameters were configured correctly.
        self.runtime.application_parameters();
    }

    async fn execute_operation(&mut self, operation: SwapOperation) -> SwapResponse {
        SwapResponse::Ok
    }

    async fn execute_message(&mut self, _message: ()) {
        panic!("Swap application doesn't support any cross-chain messages");
    }

    async fn store(mut self) {
        self.state.save().await.expect("Failed to save state");
    }
}

#[cfg(test)]
mod tests {
    use futures::FutureExt as _;
    use linera_sdk::{util::BlockingWait, views::View, Contract, ContractRuntime};

    use super::{SwapContract, SwapState};

    #[test]
    fn operation() {}

    #[test]
    #[should_panic(expected = "Swap application doesn't support any cross-chain messages")]
    fn message() {}

    #[test]
    fn cross_application_call() {}

    fn create_and_instantiate_swap(initial_value: u64) -> SwapContract {
        let runtime = ContractRuntime::new().with_application_parameters(());
        let mut contract = SwapContract {
            state: SwapState::load(runtime.root_view_storage_context())
                .blocking_wait()
                .expect("Failed to read from mock key value store"),
            runtime,
        };

        contract
            .instantiate(())
            .now_or_never()
            .expect("Initialization of swap state should not await anything");

        contract
    }
}
