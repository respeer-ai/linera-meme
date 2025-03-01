// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

#![cfg_attr(target_arch = "wasm32", no_main)]

mod state;

use abi::swap::liquidity_rfq::{
    LiquidityRfqAbi, LiquidityRfqMessage, LiquidityRfqOperation, LiquidityRfqParameters,
    LiquidityRfqResponse,
};
use linera_sdk::{
    base::WithContractAbi,
    views::{RootView, View},
    Contract, ContractRuntime,
};

use self::state::LiquidityRfqState;

pub struct LiquidityRfqContract {
    state: LiquidityRfqState,
    runtime: ContractRuntime<Self>,
}

linera_sdk::contract!(LiquidityRfqContract);

impl WithContractAbi for LiquidityRfqContract {
    type Abi = LiquidityRfqAbi;
}

impl Contract for LiquidityRfqContract {
    type Message = LiquidityRfqMessage;
    type InstantiationArgument = ();
    type Parameters = LiquidityRfqParameters;

    async fn load(runtime: ContractRuntime<Self>) -> Self {
        let state = LiquidityRfqState::load(runtime.root_view_storage_context())
            .await
            .expect("Failed to load state");
        LiquidityRfqContract { state, runtime }
    }

    async fn instantiate(&mut self, _argument: ()) {
        // Validate that the application parameters were configured correctly.
        self.runtime.application_parameters();

        self.state.initialized.set(true);
    }

    async fn execute_operation(
        &mut self,
        operation: LiquidityRfqOperation,
    ) -> LiquidityRfqResponse {
        LiquidityRfqResponse::Ok
    }

    async fn execute_message(&mut self, message: LiquidityRfqMessage) {
        panic!("LiquidityRfq application doesn't support any cross-chain messages");
    }

    async fn store(mut self) {
        self.state.save().await.expect("Failed to save state");
    }
}

#[cfg(test)]
mod tests {
    use abi::swap::liquidity_rfq::LiquidityRfqParameters;
    use futures::FutureExt as _;
    use linera_sdk::{
        base::ApplicationId, util::BlockingWait, views::View, Contract, ContractRuntime,
    };
    use std::str::FromStr;

    use super::{LiquidityRfqContract, LiquidityRfqState};

    #[test]
    fn operation() {}

    #[test]
    fn message() {}

    #[test]
    fn cross_application_call() {}

    fn create_and_instantiate_liquidity_rfq() -> LiquidityRfqContract {
        let application_id_str = "d50e0708b6e799fe2f93998ce03b4450beddc2fa934341a3e9c9313e3806288603d504225198c624908c6b0402dc83964be708e42f636dea109e2a82e9f52b58899dd894c41297e9dd1221fa02845efc81ed8abd9a0b7d203ad514b3aa6b2d46010000000000000000000000";
        let application_id = ApplicationId::from_str(application_id_str).unwrap();
        let runtime = ContractRuntime::new().with_application_parameters(LiquidityRfqParameters {
            token_0: application_id,
            token_1: None,
        });
        let mut contract = LiquidityRfqContract {
            state: LiquidityRfqState::load(runtime.root_view_storage_context())
                .blocking_wait()
                .expect("Failed to read from mock key value store"),
            runtime,
        };

        contract
            .instantiate(())
            .now_or_never()
            .expect("Initialization of liquidity rfq state should not await anything");

        assert_eq!(*contract.state.initialized.get(), true);

        contract
    }
}
