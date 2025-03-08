// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

#![cfg_attr(target_arch = "wasm32", no_main)]

mod state;

use abi::swap::pool::{
    InstantiationArgument, PoolAbi, PoolMessage, PoolOperation, PoolParameters, PoolResponse,
};
use linera_sdk::{
    linera_base_types::{Account, AccountOwner, Amount, WithContractAbi},
    views::{RootView, View},
    Contract, ContractRuntime,
};
use pool::PoolError;

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
    type Message = PoolMessage;
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
        let parameters = self.runtime.application_parameters();

        let creator = self.owner_account();
        let timestamp = self.runtime.system_time();
        self.state
            .instantiate(argument.clone(), parameters, creator, timestamp);
    }

    async fn execute_operation(&mut self, operation: PoolOperation) -> PoolResponse {
        PoolResponse::Ok
    }

    async fn execute_message(&mut self, message: PoolMessage) {}

    async fn store(mut self) {
        self.state.save().await.expect("Failed to save state");
    }
}

impl PoolContract {
    fn virtual_initial_liquidity(&mut self) -> bool {
        self.runtime
            .application_parameters()
            .virtual_initial_liquidity
    }

    fn owner_account(&mut self) -> Account {
        Account {
            chain_id: self.runtime.chain_id(),
            owner: match self.runtime.authenticated_signer() {
                Some(owner) => Some(AccountOwner::User(owner)),
                _ => None,
            },
        }
    }
}

#[cfg(test)]
mod tests {
    use abi::swap::pool::{InstantiationArgument, PoolAbi, PoolMessage, PoolParameters};
    use futures::FutureExt as _;
    use linera_sdk::{
        linera_base_types::{Amount, ApplicationId, ChainId, Owner},
        util::BlockingWait,
        views::View,
        Contract, ContractRuntime,
    };
    use std::str::FromStr;

    use super::{PoolContract, PoolState};

    #[tokio::test(flavor = "multi_thread")]
    async fn create_pool_with_liquidity() {
        let mut pool = create_and_instantiate_pool();
    }

    #[test]
    fn message() {}

    #[test]
    fn cross_application_call() {}

    fn create_and_instantiate_pool() -> PoolContract {
        let _ = env_logger::builder().is_test(true).try_init();

        let token_0 = ApplicationId::from_str("b94e486abcfc016e937dad4297523060095f405530c95d498d981a94141589f167693295a14c3b48460ad6f75d67d2414428227550eb8cee8ecaa37e8646518300aee928d4bf3880353b4a3cd9b6f88e6cc6e5ed050860abae439e7782e9b2dfe8020000000000000000000000").unwrap();
        let token_1 = ApplicationId::from_str("b94e486abcfc016e937dad4297523060095f405530c95d498d981a94141589f167693295a14c3b48460ad6f75d67d2414428227550eb8cee8ecaa37e8646518300aee928d4bf3880353b4a3cd9b6f88e6cc6e5ed050860abae439e7782e9b2dfe8020000000000000000000001").unwrap();
        let router_application_id = ApplicationId::from_str("b94e486abcfc016e937dad4297523060095f405530c95d498d981a94141589f167693295a14c3b48460ad6f75d67d2414428227550eb8cee8ecaa37e8646518300aee928d4bf3880353b4a3cd9b6f88e6cc6e5ed050860abae439e7782e9b2dfe8020000000000000000000002").unwrap();
        let chain_id =
            ChainId::from_str("aee928d4bf3880353b4a3cd9b6f88e6cc6e5ed050860abae439e7782e9b2dfe8")
                .unwrap();
        let application_id = ApplicationId::from_str("b94e486abcfc016e937dad4297523060095f405530c95d498d981a94141589f167693295a14c3b48460ad6f75d67d2414428227550eb8cee8ecaa37e8646518300aee928d4bf3880353b4a3cd9b6f88e6cc6e5ed050860abae439e7782e9b2dfe8020000000000000000000005").unwrap().with_abi::<PoolAbi>();
        let owner =
            Owner::from_str("5279b3ae14d3b38e14b65a74aefe44824ea88b25c7841836e9ec77d991a5bc7f")
                .unwrap();
        let runtime = ContractRuntime::new()
            .with_application_parameters(PoolParameters {
                token_0,
                token_1: Some(token_1),
                virtual_initial_liquidity: true,
            })
            .with_chain_id(chain_id)
            .with_application_id(application_id)
            .with_system_time(0.into())
            .with_authenticated_signer(owner);
        let mut contract = PoolContract {
            state: PoolState::load(runtime.root_view_storage_context())
                .blocking_wait()
                .expect("Failed to read from mock key value store"),
            runtime,
        };

        contract
            .instantiate(InstantiationArgument {
                amount_0: Amount::ONE,
                amount_1: Amount::ONE,
                pool_fee_percent: 30,
                protocol_fee_percent: 5,
                router_application_id,
            })
            .now_or_never()
            .expect("Initialization of pool state should not await anything");

        contract
    }
}
