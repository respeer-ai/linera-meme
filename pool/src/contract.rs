// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

#![cfg_attr(target_arch = "wasm32", no_main)]

mod state;

use abi::{
    meme::{MemeAbi, MemeOperation, MemeResponse},
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
            _ => todo!(),
        }
    }

    async fn execute_message(&mut self, message: PoolMessage) {
        match message {
            PoolMessage::RequestFund {
                token,
                transfer_id,
                amount,
            } => self
                .on_msg_request_fund(token, transfer_id, amount)
                .expect("Failed MSG: request fund"),
            PoolMessage::FundSuccess { transfer_id } => self
                .on_msg_fund_success(transfer_id)
                .await
                .expect("Failed MSG: funds success"),
            PoolMessage::FundFail { transfer_id, error } => self
                .on_msg_fund_fail(transfer_id, error)
                .await
                .expect("Failed MSG: funds fail"),
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

    fn application_creation_account(&mut self) -> Account {
        Account {
            chain_id: self.runtime.application_id().creation.chain_id,
            owner: Some(AccountOwner::Application(
                self.runtime.application_id().forget_abi(),
            )),
        }
    }

    fn application_chain_account(&mut self) -> Account {
        Account {
            chain_id: self.runtime.chain_id(),
            owner: Some(AccountOwner::Application(
                self.runtime.application_id().forget_abi(),
            )),
        }
    }

    // Send a message to token chain, then call token application
    // Send back a message of fund result
    fn transfer_token_funds(&mut self, token: ApplicationId, amount: Amount, transfer_id: u64) {
        self.runtime
            .prepare_message(PoolMessage::RequestFund {
                token,
                transfer_id,
                amount,
            })
            .with_authentication()
            .send_to(token.creation.chain_id);
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
            !(amount_0_in.is_some() && amount_1_in.is_some())
                && (amount_0_in.is_some() || amount_1_in.is_some()),
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
                error: None,
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
                error: None,
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

    fn transfer_meme(&mut self, token: ApplicationId, to: Account, amount: Amount) {
        let call = MemeOperation::Transfer { to, amount };
        let _ = self
            .runtime
            .call_application(true, token.with_abi::<MemeAbi>(), &call);
    }

    fn transfer_meme_to_creation_chain_application(&mut self, fund_request: &FundRequest) {
        let application = self.application_creation_account();
        self.transfer_meme(fund_request.token, application, fund_request.amount_in);
    }

    fn swap_fund_success(&mut self, fund_request: &FundRequest) {
        // 1: Still on caller chain, need to fund creation chain firstly
        self.transfer_meme_to_creation_chain_application(fund_request);
        // 2: Let creation chain do swap
        self.runtime
            .prepare_message(PoolMessage::Swap {
                origin: fund_request.from,
                amount_0_in: if fund_request.token == self.state.token_0() {
                    Some(fund_request.amount_in)
                } else {
                    None
                },
                amount_1_in: if fund_request.token == self.state.token_0() {
                    None
                } else {
                    Some(fund_request.amount_in)
                },
                amount_0_out_min: if fund_request.token == self.state.token_0() {
                    None
                } else {
                    fund_request.pair_token_amount_out_min
                },
                amount_1_out_min: if fund_request.token == self.state.token_0() {
                    fund_request.pair_token_amount_out_min
                } else {
                    None
                },
                to: fund_request.to,
                block_timestamp: fund_request.block_timestamp,
            })
            .with_authentication()
            .send_to(self.runtime.application_id().creation.chain_id);
    }

    fn add_liquidity_fund_success(&mut self, fund_request: &FundRequest) {}

    async fn on_msg_fund_success(&mut self, transfer_id: u64) -> Result<(), PoolError> {
        let fund_request = self.state.fund_request(transfer_id).await?;

        self.state
            .update_fund_request(transfer_id, FundStatus::Success, None)
            .await?;

        match fund_request.fund_type {
            FundType::Swap => self.swap_fund_success(&fund_request),
            FundType::AddLiquidity => self.add_liquidity_fund_success(&fund_request),
        };

        Ok(())
    }

    async fn on_msg_fund_fail(&mut self, transfer_id: u64, error: String) -> Result<(), PoolError> {
        let _ = self.state.fund_request(transfer_id).await?;
        self.state
            .update_fund_request(transfer_id, FundStatus::Fail, Some(error))
            .await?;

        // TODO: return amount of token_0

        Ok(())
    }

    // Always be run on meme chain
    fn on_msg_request_fund(
        &mut self,
        token: ApplicationId,
        transfer_id: u64,
        amount: Amount,
    ) -> Result<(), PoolError> {
        let application_id = self.runtime.application_id().forget_abi();

        let call = MemeOperation::TransferToCaller {
            transfer_id,
            amount,
        };

        let message_chain_id = self.runtime.message_id().unwrap().chain_id;
        match self
            .runtime
            .call_application(true, token.with_abi::<MemeAbi>(), &call)
        {
            MemeResponse::Ok => {
                self.runtime
                    .prepare_message(PoolMessage::FundSuccess { transfer_id })
                    .with_authentication()
                    .send_to(message_chain_id);
            }
            MemeResponse::Fail(error) => {
                self.runtime
                    .prepare_message(PoolMessage::FundFail { transfer_id, error })
                    .with_authentication()
                    .send_to(message_chain_id);
            }
        };
        Ok(())
    }

    // Always be run on creation chain
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
        // Here we already funded
        // 1: Calculate pair token amount
        let amount_0_out = if let Some(amount_1_in) = amount_1_in {
            self.state.calculate_swap_amount_0(amount_1_in)?
        } else {
            Amount::ZERO
        };
        if let Some(amount_0_out_min) = amount_0_out_min {
            if amount_0_out < amount_0_out_min {
                return Err(PoolError::InvalidAmount);
            }
        }

        let amount_1_out = if let Some(amount_0_in) = amount_0_in {
            self.state.calculate_swap_amount_1(amount_0_in)?
        } else {
            Amount::ZERO
        };
        if let Some(amount_1_out_min) = amount_1_out_min {
            if amount_1_out < amount_1_out_min {
                return Err(PoolError::InvalidAmount);
            }
        }

        if amount_0_out == Amount::ZERO && amount_1_out == Amount::ZERO {
            return Err(PoolError::InvalidAmount);
        }

        // 2: Check liquidity
        let _ = self
            .state
            .calculate_adjusted_amount_pair(amount_0_out, amount_1_out)?;

        // 3: Transfer token
        let to = to.unwrap_or(origin);
        let application = AccountOwner::Application(self.runtime.application_id().forget_abi());

        if amount_0_out > Amount::ZERO {
            self.transfer_meme(self.state.token_0(), to, amount_0_out);
        }
        if amount_1_out > Amount::ZERO {
            if let Some(token_1) = self.state.token_1() {
                self.transfer_meme(token_1, to, amount_1_out);
            } else {
                self.runtime.transfer(Some(application), to, amount_1_out);
            }
        }

        // 4: Liquid

        let balance_0 = self.state.reserve_0().saturating_sub(amount_0_out);
        let balance_1 = self.state.reserve_1().saturating_add(amount_1_out);
        let timestamp = self.runtime.system_time();

        self.state.liquid(balance_0, balance_1, timestamp);

        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use abi::swap::pool::{
        InstantiationArgument, PoolAbi, PoolMessage, PoolOperation, PoolParameters, PoolResponse,
    };
    use futures::FutureExt as _;
    use linera_sdk::{
        linera_base_types::{
            Account, AccountOwner, Amount, ApplicationId, ChainId, MessageId, Owner,
        },
        util::BlockingWait,
        views::View,
        Contract, ContractRuntime,
    };
    use pool::{FundRequest, FundStatus, FundType};
    use std::str::FromStr;

    use super::{PoolContract, PoolState};

    #[tokio::test(flavor = "multi_thread")]
    async fn create_pool_with_real_liquidity() {
        let pool = create_and_instantiate_pool(false);
        let _ = pool.state.pool();
    }

    #[tokio::test(flavor = "multi_thread")]
    async fn create_pool_with_virtual_liquidity() {
        let pool = create_and_instantiate_pool(true);
        let _ = pool.state.pool();
    }

    #[tokio::test(flavor = "multi_thread")]
    async fn operation_swap() {
        let mut pool = create_and_instantiate_pool(true);

        let response = pool
            .execute_operation(PoolOperation::Swap {
                amount_0_in: None,
                amount_1_in: Some(Amount::ONE),
                amount_0_out_min: None,
                amount_1_out_min: None,
                to: None,
                block_timestamp: None,
            })
            .now_or_never()
            .expect("Execution of meme operation should not await anything");

        assert!(matches!(response, PoolResponse::Ok));
    }

    #[tokio::test(flavor = "multi_thread")]
    async fn message_request_fund() {
        let mut pool = create_and_instantiate_pool(true);

        pool.execute_message(PoolMessage::RequestFund {
            token: pool.state.token_0(),
            transfer_id: 1000,
            amount: Amount::ONE,
        })
        .await;
    }

    #[tokio::test(flavor = "multi_thread")]
    async fn message_fund_success() {
        let mut pool = create_and_instantiate_pool(true);
        let owner = Account {
            chain_id: pool.runtime.chain_id(),
            owner: Some(AccountOwner::User(
                pool.runtime.authenticated_signer().unwrap(),
            )),
        };

        let fund_request = FundRequest {
            from: owner,
            token: pool.state.token_0(),
            amount_in: Amount::ONE,
            pair_token_amount_out_min: None,
            to: None,
            block_timestamp: None,
            fund_type: FundType::Swap,
            status: FundStatus::InFlight,
            error: None,
            next_request: None,
        };

        let transfer_id = pool.state.create_fund_request(fund_request).unwrap();
        pool.execute_message(PoolMessage::FundSuccess { transfer_id })
            .await;
    }

    #[tokio::test(flavor = "multi_thread")]
    async fn message_fund_fail() {
        let mut pool = create_and_instantiate_pool(true);
        let owner = Account {
            chain_id: pool.runtime.chain_id(),
            owner: Some(AccountOwner::User(
                pool.runtime.authenticated_signer().unwrap(),
            )),
        };

        let fund_request = FundRequest {
            from: owner,
            token: pool.state.token_0(),
            amount_in: Amount::ONE,
            pair_token_amount_out_min: None,
            to: None,
            block_timestamp: None,
            fund_type: FundType::Swap,
            status: FundStatus::InFlight,
            error: None,
            next_request: None,
        };

        let transfer_id = pool.state.create_fund_request(fund_request).unwrap();
        pool.execute_message(PoolMessage::FundFail {
            transfer_id,
            error: "Error".to_string(),
        })
        .await;
    }

    #[tokio::test(flavor = "multi_thread")]
    async fn message_swap() {
        let mut pool = create_and_instantiate_pool(true);
        let owner = Account {
            chain_id: pool.runtime.chain_id(),
            owner: Some(AccountOwner::User(
                pool.runtime.authenticated_signer().unwrap(),
            )),
        };

        pool.execute_message(PoolMessage::Swap {
            origin: owner,
            amount_0_in: None,
            amount_1_in: Some(Amount::ONE),
            amount_0_out_min: None,
            amount_1_out_min: None,
            to: None,
            block_timestamp: None,
        })
        .await;
    }

    #[test]
    fn cross_application_call() {}

    fn mock_application_call(
        _authenticated: bool,
        _application_id: ApplicationId,
        _operation: Vec<u8>,
    ) -> Vec<u8> {
        vec![0]
    }

    fn create_and_instantiate_pool(virtual_initial_liquidity: bool) -> PoolContract {
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
        let message_id = MessageId::from_str("dad01517c7a3c428ea903253a9e59964e8db06d323a9bd3f4c74d6366832bdbf801200000000000000000000").unwrap();
        let runtime = ContractRuntime::new()
            .with_application_parameters(PoolParameters {
                token_0,
                token_1: Some(token_1),
                virtual_initial_liquidity,
            })
            .with_chain_id(chain_id)
            .with_application_id(application_id)
            .with_authenticated_caller_id(router_application_id)
            .with_call_application_handler(mock_application_call)
            .with_system_time(0.into())
            .with_message_id(message_id)
            .with_authenticated_signer(owner);
        let mut contract = PoolContract {
            state: PoolState::load(runtime.root_view_storage_context())
                .blocking_wait()
                .expect("Failed to read from mock key value store"),
            runtime,
        };

        contract
            .instantiate(InstantiationArgument {
                amount_0: Amount::from_str("1000").unwrap(),
                amount_1: Amount::from_str("10").unwrap(),
                pool_fee_percent_mul_100: 30,
                protocol_fee_percent_mul_100: 5,
                router_application_id,
            })
            .now_or_never()
            .expect("Initialization of pool state should not await anything");

        contract
    }
}
