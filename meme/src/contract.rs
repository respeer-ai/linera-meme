// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

#![cfg_attr(target_arch = "wasm32", no_main)]

mod state;

use abi::meme::InstantiationArgument;
use linera_sdk::{
    base::WithContractAbi,
    views::{RootView, View},
    Contract, ContractRuntime,
};
use meme::{MemeAbi, MemeOperation, MemeResponse};

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
    use abi::{
        meme::{InstantiationArgument, Meme, Metadata, Mint},
        store_type::StoreType,
    };
    use futures::FutureExt as _;
    use linera_sdk::{base::Amount, util::BlockingWait, views::View, Contract, ContractRuntime};
    use std::collections::HashMap;
    use std::str::FromStr;

    use super::{MemeContract, MemeState};

    #[test]
    fn operation() {}

    #[test]
    #[should_panic(expected = "Meme application doesn't support any cross-chain messages")]
    fn message() {
        let mut meme = create_and_instantiate_meme();

        meme.execute_message(())
            .now_or_never()
            .expect("Execution of meme operation should not await anything");
    }

    #[test]
    fn cross_application_call() {}

    fn create_and_instantiate_meme() -> MemeContract {
        let runtime = ContractRuntime::new().with_application_parameters(());
        let mut contract = MemeContract {
            state: MemeState::load(runtime.root_view_storage_context())
                .blocking_wait()
                .expect("Failed to read from mock key value store"),
            runtime,
        };

        let instantiation_argument = InstantiationArgument {
            meme: Meme {
                name: "Test Token".to_string(),
                ticker: "LTT".to_string(),
                decimals: 6,
                initial_supply: Amount::from_tokens(21000000),
                total_supply: Amount::from_tokens(21000000),
                metadata: Metadata {
                    logo_store_type: StoreType::S3,
                    logo: "Test Logo".to_string(),
                    description: "Test token description".to_string(),
                    twitter: None,
                    telegram: None,
                    discord: None,
                    website: None,
                    github: None,
                },
            },
            mint: Some(Mint {
                fixed_currency: true,
                initial_currency: Amount::from_str("0.0000001").unwrap(),
            }),
            fee_percent: Some(Amount::from_str("0.2").unwrap()),
            blob_gateway_application_id: None,
            ams_application_id: None,
            swap_application_id: None,
            initial_balances: HashMap::new(),
        };

        contract
            .instantiate(instantiation_argument.clone())
            .now_or_never()
            .expect("Initialization of meme state should not await anything");

        assert_eq!(
            *contract.state.meme.get().as_ref().unwrap(),
            instantiation_argument.meme
        );
        assert_eq!(
            *contract.state.mint.get().as_ref().unwrap(),
            instantiation_argument.mint.unwrap()
        );
        assert_eq!(
            *contract.state.fee_percent.get().as_ref().unwrap(),
            instantiation_argument.fee_percent.unwrap()
        );

        contract
    }
}
