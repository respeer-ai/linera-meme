// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

#![cfg_attr(target_arch = "wasm32", no_main)]

mod state;

use linera_sdk::{
    base::WithContractAbi,
    views::{RootView, View},
    Contract, ContractRuntime,
};
use proxy::{InstantiationArgument, ProxyAbi, ProxyError, ProxyOperation, ProxyResponse};

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
    type InstantiationArgument = InstantiationArgument;
    type Parameters = ();

    async fn load(runtime: ContractRuntime<Self>) -> Self {
        let state = ProxyState::load(runtime.root_view_storage_context())
            .await
            .expect("Failed to load state");
        ProxyContract { state, runtime }
    }

    async fn instantiate(&mut self, argument: InstantiationArgument) {
        // Validate that the application parameters were configured correctly.
        self.runtime.application_parameters();

        let owner = self
            .runtime
            .authenticated_signer()
            .expect("Invalid creator");
        self.state.initantiate(argument, owner).await;
    }

    async fn execute_operation(&mut self, operation: ProxyOperation) -> ProxyResponse {
        ProxyResponse::Ok
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
    use linera_sdk::{
        base::BytecodeId, util::BlockingWait, views::View, Contract, ContractRuntime,
    };
    use proxy::InstantiationArgument;
    use std::str::FromStr;

    use super::{ProxyContract, ProxyState};

    #[test]
    fn operation() {}

    #[test]
    fn message() {}

    #[test]
    fn cross_application_call() {}

    fn create_and_instantiate_proxy() -> ProxyContract {
        let runtime = ContractRuntime::new().with_application_parameters(());
        let mut contract = ProxyContract {
            state: ProxyState::load(runtime.root_view_storage_context())
                .blocking_wait()
                .expect("Failed to read from mock key value store"),
            runtime,
        };

        let meme_bytecode_id = BytecodeId::from_str("58cc6e264a19cddf027010db262ca56a18e7b63e2a7ad1561ea9841f9aef308fc5ae59261c0137891a342001d3d4446a26c3666ed81aadf7e5eec6a01c86db6d").unwrap();

        contract
            .instantiate(InstantiationArgument { meme_bytecode_id })
            .now_or_never()
            .expect("Initialization of proxy state should not await anything");

        assert_eq!(
            contract.state.meme_bytecode_id.get().unwrap(),
            meme_bytecode_id
        );

        contract
    }
}
