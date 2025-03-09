// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

#![cfg_attr(target_arch = "wasm32", no_main)]

mod state;

use abi::{
    meme::{MemeAbi, MemeOperation},
    swap::pool::{
        InstantiationArgument, PoolAbi, PoolMessage, PoolOperation, PoolParameters, PoolResponse,
    },
};
use linera_sdk::{
    linera_base_types::{Account, AccountOwner, Amount, ApplicationId, Timestamp, WithContractAbi},
    views::{RootView, View},
    Contract, ContractRuntime,
};
use pool::{FundRequest, FundStatus, FundType, PoolError};

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
        // Pool application should be able to call from any chain, authorize funds on caller chain, then swap on creation chain
        // It should not be called from another application, it should be only called from user
        assert!(
            self.runtime.authenticated_signer().is_some(),
            "Invalid signer"
        );
        assert!(
            self.runtime.authenticated_caller_id().is_none(),
            "Invalid caller"
        );

        match operation {
            PoolOperation::Swap {
                amount_0_in,
                amount_1_in,
                amount_0_out_min,
                amount_1_out_min,
                to,
                block_timestamp,
            } => self
                .on_op_swap(
                    amount_0_in,
                    amount_1_in,
                    amount_0_out_min,
                    amount_1_out_min,
                    to,
                    block_timestamp,
                )
                .expect("Failed OP: swap"),
            // Executed on caller chain of Approve
            PoolOperation::FundsSuccess { transfer_id } => self
                .on_op_funds_success(transfer_id)
                .expect("Failed OP: funds success"),
            PoolOperation::FundsFail { transfer_id } => self
                .on_op_funds_fail(transfer_id)
                .expect("Failed OP: funds fail"),
            _ => todo!(),
        }
    }

    async fn execute_message(&mut self, message: PoolMessage) {
        match message {
            PoolMessage::Swap {
                origin,
                amount_0_in,
                amount_1_in,
                amount_0_out_min,
                amount_1_out_min,
                to,
                block_timestamp,
            } => self
                .on_msg_swap(
                    origin,
                    amount_0_in,
                    amount_1_in,
                    amount_0_out_min,
                    amount_1_out_min,
                    to,
                    block_timestamp,
                )
                .expect("Failed MSG: swap"),
        }
    }

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

    fn application_creation_account(&self, application_id: ApplicationId) -> Account {
        Account {
            chain_id: application_id.creation.chain_id,
            owner: Some(AccountOwner::Application(application_id)),
        }
    }

    fn application_chain_account(&mut self, application_id: ApplicationId) -> Account {
        Account {
            chain_id: self.runtime.chain_id(),
            owner: Some(AccountOwner::Application(application_id)),
        }
    }

    fn transfer_token_funds(&mut self, token: ApplicationId, amount: Amount, transfer_id: u64) {
        let chain_id = self.runtime.chain_id();
        let application_id = self.runtime.application_id().forget_abi();

        let call = MemeOperation::TransferToCaller {
            transfer_id,
            amount,
        };

        let _ = self
            .runtime
            .call_application(true, token.with_abi::<MemeAbi>(), &call);
    }

    fn transfer_token_0_funds(&mut self, amount: Amount, transfer_id: u64) {
        let token_0 = self.state.token_0();
        self.transfer_token_funds(token_0, amount, transfer_id);
    }

    fn fund_pool_application_creation_chain(&mut self, amount: Amount) {
        let chain_id = self.runtime.application_id().creation.chain_id;
        let application_id = self.runtime.application_id().forget_abi();
        let owner = AccountOwner::User(self.runtime.authenticated_signer().unwrap());
        let application = Account {
            chain_id,
            owner: Some(AccountOwner::Application(application_id)),
        };

        let owner_balance = self.runtime.owner_balance(owner);
        let chain_balance = self.runtime.chain_balance();

        let from_owner_balance = if amount <= owner_balance {
            amount
        } else {
            owner_balance
        };
        let from_chain_balance = if amount <= owner_balance {
            Amount::ZERO
        } else {
            amount.try_sub(owner_balance).expect("Invalid amount")
        };

        assert!(from_owner_balance <= owner_balance, "Insufficient balance");
        assert!(from_chain_balance <= chain_balance, "Insufficient balance");

        if from_owner_balance > Amount::ZERO {
            self.runtime
                .transfer(Some(owner), application, from_owner_balance);
        }
        if from_chain_balance > Amount::ZERO {
            self.runtime.transfer(None, application, from_chain_balance);
        }
    }

    fn on_op_swap(
        &mut self,
        amount_0_in: Option<Amount>,
        amount_1_in: Option<Amount>,
        amount_0_out_min: Option<Amount>,
        amount_1_out_min: Option<Amount>,
        to: Option<Account>,
        block_timestamp: Option<Timestamp>,
    ) -> Result<PoolResponse, PoolError> {
        assert!(
            amount_0_in.is_some() && amount_1_in.is_some(),
            "Invalid amount"
        );

        let origin = self.owner_account();

        // 1: Authorize funds of token_0
        if let Some(amount_0_in) = amount_0_in {
            let fund_request = FundRequest {
                from: origin,
                token: self.state.token_0(),
                amount_in: amount_0_in,
                pair_token_amount_out_min: amount_1_out_min,
                to,
                block_timestamp,
                fund_type: FundType::Swap,
                status: FundStatus::InFlight,
                next_request: None,
            };

            let transfer_id = self.state.create_fund_request(fund_request)?;
            self.transfer_token_0_funds(amount_0_in, transfer_id);
            return Ok(PoolResponse::Ok);
        }

        let Some(amount) = amount_1_in else {
            panic!("Invalid amount");
        };
        if let Some(token_1) = self.state.token_1() {
            let fund_request = FundRequest {
                from: origin,
                token: token_1,
                amount_in: amount,
                pair_token_amount_out_min: amount_0_out_min,
                to,
                block_timestamp,
                fund_type: FundType::Swap,
                status: FundStatus::InFlight,
                next_request: None,
            };

            let transfer_id = self.state.create_fund_request(fund_request)?;
            self.transfer_token_funds(token_1, amount, transfer_id);
            return Ok(PoolResponse::Ok);
        }

        // Should transfer back to origin if amount requirement don't satisfied
        self.fund_pool_application_creation_chain(amount);
        self.runtime
            .prepare_message(PoolMessage::Swap {
                origin,
                amount_0_in,
                amount_1_in,
                amount_0_out_min,
                amount_1_out_min,
                to,
                block_timestamp,
            })
            .with_authentication()
            .send_to(self.runtime.application_id().creation.chain_id);

        // 2: Authorize funds of token_1, or transfer native funds (will be done in message)
        Ok(PoolResponse::Ok)
    }

    fn on_op_funds_success(&mut self, transfer_id: u64) -> Result<PoolResponse, PoolError> {
        let token = self.runtime.application_id().forget_abi();
        self.state.validate_token(token);

        // let fund_request = self.state.fund_request(transfer_id)?;

        Ok(PoolResponse::Ok)
    }

    fn on_op_funds_fail(&mut self, transfer_id: u64) -> Result<PoolResponse, PoolError> {
        let token = self.runtime.application_id().forget_abi();
        self.state.validate_token(token);
        Ok(PoolResponse::Ok)
    }

    fn on_msg_swap(
        &mut self,
        origin: Account,
        amount_0_in: Option<Amount>,
        amount_1_in: Option<Amount>,
        amount_0_out_min: Option<Amount>,
        amount_1_out_min: Option<Amount>,
        to: Option<Account>,
        block_timestamp: Option<Timestamp>,
    ) -> Result<(), PoolError> {
        Ok(())
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
