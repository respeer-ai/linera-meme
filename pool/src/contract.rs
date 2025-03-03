// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

#![cfg_attr(target_arch = "wasm32", no_main)]

mod state;

use abi::swap::pool::{
    InstantiationArgument, PoolAbi, PoolOperation, PoolParameters, PoolResponse,
};
use linera_sdk::{
    base::WithContractAbi,
    views::{RootView, View},
    Contract, ContractRuntime,
};

use self::state::PoolState;

pub struct PoolContract {
    state: PoolState,
    runtime: ContractRuntime<Self>,
}

linera_sdk::contract!(PoolContract);

impl WithContractAbi for PoolContract {
    type Abi = PoolAbi;
}

impl Contract for PoolContract {
    type Message = ();
    type InstantiationArgument = InstantiationArgument;
    type Parameters = PoolParameters;

    async fn load(runtime: ContractRuntime<Self>) -> Self {
        let state = PoolState::load(runtime.root_view_storage_context())
            .await
            .expect("Failed to load state");
        PoolContract { state, runtime }
    }

    async fn instantiate(&mut self, argument: InstantiationArgument) {
        // Validate that the application parameters were configured correctly.
        self.runtime.application_parameters();

        log::info!("Chain balance {}", self.runtime.chain_balance());
    }

    async fn execute_operation(&mut self, operation: PoolOperation) -> PoolResponse {
        PoolResponse::Ok
    }

    async fn execute_message(&mut self, _message: ()) {
        panic!("Pool application doesn't support any cross-chain messages");
    }

    async fn store(mut self) {
        self.state.save().await.expect("Failed to save state");
    }
}

#[cfg(test)]
mod tests {
    use futures::FutureExt as _;
    use linera_sdk::{util::BlockingWait, views::View, Contract, ContractRuntime};

    use super::{PoolContract, PoolState};

    #[test]
    fn operation() {
        let initial_value = 72_u64;
        let mut pool = create_and_instantiate_pool(initial_value);

        let increment = 42_308_u64;

        let response = pool
            .execute_operation(increment)
            .now_or_never()
            .expect("Execution of pool operation should not await anything");

        let expected_value = initial_value + increment;

        assert_eq!(response, expected_value);
        assert_eq!(*pool.state.value.get(), initial_value + increment);
    }

    #[test]
    #[should_panic(expected = "Pool application doesn't support any cross-chain messages")]
    fn message() {
        let initial_value = 72_u64;
        let mut pool = create_and_instantiate_pool(initial_value);

        pool.execute_message(())
            .now_or_never()
            .expect("Execution of pool operation should not await anything");
    }

    #[test]
    fn cross_application_call() {
        let initial_value = 2_845_u64;
        let mut pool = create_and_instantiate_pool(initial_value);

        let increment = 8_u64;

        let response = pool
            .execute_operation(increment)
            .now_or_never()
            .expect("Execution of pool operation should not await anything");

        let expected_value = initial_value + increment;

        assert_eq!(response, expected_value);
        assert_eq!(*pool.state.value.get(), expected_value);
    }

    fn create_and_instantiate_pool(initial_value: u64) -> PoolContract {
        let runtime = ContractRuntime::new().with_application_parameters(());
        let mut contract = PoolContract {
            state: PoolState::load(runtime.root_view_storage_context())
                .blocking_wait()
                .expect("Failed to read from mock key value store"),
            runtime,
        };

        contract
            .instantiate(initial_value)
            .now_or_never()
            .expect("Initialization of pool state should not await anything");

        assert_eq!(*contract.state.value.get(), initial_value);

        contract
    }
}
