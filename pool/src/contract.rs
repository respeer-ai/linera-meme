// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

#![cfg_attr(target_arch = "wasm32", no_main)]

mod state;

use abi::{
    meme::{MemeAbi, MemeOperation, MemeResponse},
    policy::open_chain_fee_budget,
    swap::{
        pool::{
            InstantiationArgument, PoolAbi, PoolMessage, PoolOperation, PoolParameters,
            PoolResponse,
        },
        router::{SwapAbi, SwapOperation},
        transaction::Transaction,
    },
};
use linera_sdk::{
    linera_base_types::{
        Account, AccountOwner, Amount, ApplicationId, ChainId, Timestamp, WithContractAbi,
    },
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
    type EventValue = ();

    async fn load(runtime: ContractRuntime<Self>) -> Self {
        let state = PoolState::load(runtime.root_view_storage_context())
            .await
            .expect("Failed to load state");
        PoolContract { state, runtime }
    }

    async fn instantiate(&mut self, argument: InstantiationArgument) {
        // Validate that the application parameters were configured correctly.
        let parameters = self.runtime.application_parameters();

        let creator = self.creator();
        let timestamp = self.runtime.system_time();
        let liquidity = self
            .state
            .instantiate(argument.clone(), parameters, creator, timestamp)
            .await
            .expect("Failed instantiate");

        if argument.amount_0 <= Amount::ZERO || argument.amount_1 <= Amount::ZERO {
            return;
        }

        let transaction = self.state.build_transaction(
            creator,
            Some(argument.amount_0),
            Some(argument.amount_1),
            None,
            None,
            Some(liquidity),
            timestamp,
        );
        let chain_id = self.runtime.chain_id();
        self.runtime
            .prepare_message(PoolMessage::NewTransaction { transaction })
            .with_authentication()
            .send_to(chain_id);
    }

    async fn execute_operation(&mut self, operation: PoolOperation) -> PoolResponse {
        // Pool application should be able to call from any chain, authorize funds on caller chain, then swap on creation chain
        // It should not be called from another application, it should be only called from user
        assert!(
            self.runtime.authenticated_signer().is_some(),
            "Invalid signer"
        );

        match operation {
            PoolOperation::SetFeeTo { account } => self
                .on_op_set_fee_to(account)
                .expect("Failed OP: set fee to"),
            PoolOperation::SetFeeToSetter { account } => self
                .on_op_set_fee_to_setter(account)
                .expect("Failed OP: set fee to setter"),
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
            PoolOperation::AddLiquidity {
                amount_0_in,
                amount_1_in,
                amount_0_out_min,
                amount_1_out_min,
                to,
                block_timestamp,
            } => self
                .on_op_add_liquidity(
                    amount_0_in,
                    amount_1_in,
                    amount_0_out_min,
                    amount_1_out_min,
                    to,
                    block_timestamp,
                )
                .await
                .expect("Failed OP: add liquidity"),
            PoolOperation::RemoveLiquidity {
                liquidity,
                amount_0_out_min,
                amount_1_out_min,
                to,
                block_timestamp,
            } => self
                .on_op_remove_liquidity(
                    liquidity,
                    amount_0_out_min,
                    amount_1_out_min,
                    to,
                    block_timestamp,
                )
                .expect("Failed OP: remove liquidity"),
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
            PoolMessage::AddLiquidity {
                origin,
                amount_0_in,
                amount_1_in,
                amount_0_out_min,
                amount_1_out_min,
                to,
                block_timestamp,
            } => self
                .on_msg_add_liquidity(
                    origin,
                    amount_0_in,
                    amount_1_in,
                    amount_0_out_min,
                    amount_1_out_min,
                    to,
                    block_timestamp,
                )
                .await
                .expect("Failed MSG: add liquidity"),
            PoolMessage::RemoveLiquidity {
                origin,
                liquidity,
                amount_0_out_min,
                amount_1_out_min,
                to,
                block_timestamp,
            } => self
                .on_msg_remove_liquidity(
                    origin,
                    liquidity,
                    amount_0_out_min,
                    amount_1_out_min,
                    to,
                    block_timestamp,
                )
                .await
                .expect("Failed MSG: remove liquidity"),
            PoolMessage::SetFeeTo { operator, account } => self
                .on_msg_set_fee_to(operator, account)
                .expect("Failed MSG: set fee to"),
            PoolMessage::SetFeeToSetter { operator, account } => self
                .on_msg_set_fee_to_setter(operator, account)
                .expect("Failed MSG: set fee to setter"),
            PoolMessage::NewTransaction { transaction } => self
                .on_msg_new_transaction(transaction)
                .expect("Failed MSG: new transaction"),
        }
    }

    async fn store(mut self) {
        self.state.save().await.expect("Failed to save state");
    }
}

impl PoolContract {
    fn creator(&mut self) -> Account {
        self.runtime.application_parameters().creator
    }

    fn owner_account(&mut self) -> Account {
        Account {
            chain_id: self.runtime.chain_id(),
            owner: match self.runtime.authenticated_signer() {
                Some(owner) => owner,
                _ => AccountOwner::CHAIN,
            },
        }
    }

    fn application_creation_account(&mut self) -> Account {
        Account {
            chain_id: self.runtime.application_creator_chain_id(),
            owner: AccountOwner::from(self.runtime.application_id().forget_abi()),
        }
    }

    fn token_0(&mut self) -> ApplicationId {
        self.runtime.application_parameters().token_0
    }

    fn token_1(&mut self) -> Option<ApplicationId> {
        self.runtime.application_parameters().token_1
    }

    fn token_0_creator_chain_id(&mut self) -> ChainId {
        self.runtime
            .application_parameters()
            .token_0_creator_chain_id
    }

    fn token_1_creator_chain_id(&mut self) -> ChainId {
        self.runtime
            .application_parameters()
            .token_1_creator_chain_id
            .unwrap()
    }

    // Send a message to token chain, then call token application
    // Send back a message of fund result
    fn transfer_token_funds(
        &mut self,
        token_creator_chain_id: ChainId,
        token: ApplicationId,
        amount: Amount,
        transfer_id: u64,
    ) {
        self.runtime
            .prepare_message(PoolMessage::RequestFund {
                token,
                transfer_id,
                amount,
            })
            .with_authentication()
            .send_to(token_creator_chain_id);
    }

    fn transfer_token_0_funds(&mut self, amount: Amount, transfer_id: u64) {
        let token_0 = self.token_0();
        let chain_id = self.token_0_creator_chain_id();
        self.transfer_token_funds(chain_id, token_0, amount, transfer_id);
    }

    fn fund_pool_application_creation_chain(&mut self, amount: Amount) {
        let chain_id = self.runtime.application_creator_chain_id();
        let application_id = self.runtime.application_id().forget_abi();
        let owner = self.runtime.authenticated_signer().unwrap();
        let application = Account {
            chain_id,
            owner: AccountOwner::from(application_id),
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
                .transfer(owner, application, from_owner_balance);
        }
        if from_chain_balance > Amount::ZERO {
            self.runtime
                .transfer(AccountOwner::CHAIN, application, from_chain_balance);
        }
    }

    fn on_op_set_fee_to(&mut self, account: Account) -> Result<PoolResponse, PoolError> {
        let operator = self.owner_account();
        self.runtime
            .prepare_message(PoolMessage::SetFeeTo { operator, account })
            .with_authentication()
            .send_to(self.runtime.application_creator_chain_id());
        Ok(PoolResponse::Ok)
    }

    fn on_op_set_fee_to_setter(&mut self, account: Account) -> Result<PoolResponse, PoolError> {
        let operator = self.owner_account();
        self.runtime
            .prepare_message(PoolMessage::SetFeeToSetter { operator, account })
            .with_authentication()
            .send_to(self.runtime.application_creator_chain_id());
        Ok(PoolResponse::Ok)
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

        // 1: Transfer funds of token_0
        if let Some(amount_0_in) = amount_0_in {
            assert!(amount_0_in > Amount::ZERO, "Invalid amount");

            let fund_request = FundRequest {
                from: origin,
                token: Some(self.token_0()),
                amount_in: amount_0_in,
                pair_token_amount_out_min: amount_1_out_min,
                to,
                block_timestamp,
                fund_type: FundType::Swap,
                status: FundStatus::InFlight,
                error: None,
                prev_request: None,
                next_request: None,
            };

            let transfer_id = self.state.create_fund_request(fund_request)?;
            self.transfer_token_0_funds(amount_0_in, transfer_id);
            return Ok(PoolResponse::Ok);
        }

        let Some(amount) = amount_1_in else {
            panic!("Invalid amount");
        };
        assert!(amount > Amount::ZERO, "Invalid amount");

        if let Some(token_1) = self.token_1() {
            let fund_request = FundRequest {
                from: origin,
                token: Some(token_1),
                amount_in: amount,
                pair_token_amount_out_min: amount_0_out_min,
                to,
                block_timestamp,
                fund_type: FundType::Swap,
                status: FundStatus::InFlight,
                error: None,
                prev_request: None,
                next_request: None,
            };

            let transfer_id = self.state.create_fund_request(fund_request)?;
            let chain_id = self.token_1_creator_chain_id();
            self.transfer_token_funds(chain_id, token_1, amount, transfer_id);
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
            .send_to(self.runtime.application_creator_chain_id());

        // 2: Request funds of token_1, or transfer native funds (will be done in message)
        Ok(PoolResponse::Ok)
    }

    async fn on_op_add_liquidity(
        &mut self,
        amount_0_in: Amount,
        amount_1_in: Amount,
        amount_0_out_min: Option<Amount>,
        amount_1_out_min: Option<Amount>,
        to: Option<Account>,
        block_timestamp: Option<Timestamp>,
    ) -> Result<PoolResponse, PoolError> {
        assert!(
            amount_0_in > Amount::ZERO && amount_1_in > Amount::ZERO,
            "Invalid amount"
        );

        let origin = self.owner_account();

        // 1: Transfer funds of token_0
        let mut fund_request_0 = FundRequest {
            from: origin,
            token: Some(self.token_0()),
            amount_in: amount_0_in,
            pair_token_amount_out_min: amount_1_out_min,
            to,
            block_timestamp,
            fund_type: FundType::AddLiquidity,
            status: FundStatus::InFlight,
            error: None,
            prev_request: None,
            next_request: None,
        };
        let transfer_id_0 = self.state.create_fund_request(fund_request_0.clone())?;

        let fund_request_1 = FundRequest {
            from: origin,
            token: self.token_1(),
            amount_in: amount_1_in,
            pair_token_amount_out_min: amount_0_out_min,
            to,
            block_timestamp,
            fund_type: FundType::AddLiquidity,
            status: FundStatus::Created,
            error: None,
            prev_request: Some(transfer_id_0),
            next_request: None,
        };
        let transfer_id_1 = self.state.create_fund_request(fund_request_1)?;

        fund_request_0.next_request = Some(transfer_id_1);
        self.state
            .update_fund_request(transfer_id_0, fund_request_0)
            .await?;

        self.transfer_token_0_funds(amount_0_in, transfer_id_0);
        Ok(PoolResponse::Ok)
    }

    fn on_op_remove_liquidity(
        &mut self,
        liquidity: Amount,
        amount_0_out_min: Option<Amount>,
        amount_1_out_min: Option<Amount>,
        to: Option<Account>,
        block_timestamp: Option<Timestamp>,
    ) -> Result<PoolResponse, PoolError> {
        let origin = self.owner_account();
        self.runtime
            .prepare_message(PoolMessage::RemoveLiquidity {
                origin,
                liquidity,
                amount_0_out_min,
                amount_1_out_min,
                to,
                block_timestamp,
            })
            .with_authentication()
            .send_to(self.runtime.application_creator_chain_id());
        Ok(PoolResponse::Ok)
    }

    fn transfer_meme(&mut self, token: ApplicationId, to: Account, amount: Amount) {
        let call = MemeOperation::TransferFromApplication { to, amount };
        let _ = self
            .runtime
            .call_application(true, token.with_abi::<MemeAbi>(), &call);
    }

    fn transfer_meme_to_creation_chain_application(&mut self, fund_request: &FundRequest) {
        let application = self.application_creation_account();
        self.transfer_meme(
            fund_request.token.unwrap(),
            application,
            fund_request.amount_in,
        );
    }

    fn swap_fund_success(&mut self, fund_request: &FundRequest) {
        // 1: Still on caller chain, need to fund creation chain firstly
        self.transfer_meme_to_creation_chain_application(fund_request);
        // 2: Let creation chain do swap
        let token_0 = self.token_0();

        self.runtime
            .prepare_message(PoolMessage::Swap {
                origin: fund_request.from,
                amount_0_in: if fund_request.token == Some(token_0) {
                    Some(fund_request.amount_in)
                } else {
                    None
                },
                amount_1_in: if fund_request.token == Some(token_0) {
                    None
                } else {
                    Some(fund_request.amount_in)
                },
                amount_0_out_min: if fund_request.token == Some(token_0) {
                    None
                } else {
                    fund_request.pair_token_amount_out_min
                },
                amount_1_out_min: if fund_request.token == Some(token_0) {
                    fund_request.pair_token_amount_out_min
                } else {
                    None
                },
                to: fund_request.to,
                block_timestamp: fund_request.block_timestamp,
            })
            .with_authentication()
            .send_to(self.runtime.application_creator_chain_id());
    }

    async fn add_liquidity_fund_success(
        &mut self,
        fund_request: &FundRequest,
    ) -> Result<(), PoolError> {
        if let Some(transfer_id) = fund_request.next_request {
            let fund_request = self.state.fund_request(transfer_id).await?;
            if let Some(token_1) = fund_request.token {
                let chain_id = self.token_1_creator_chain_id();
                self.transfer_token_funds(chain_id, token_1, fund_request.amount_in, transfer_id);
                return Ok(());
            }

            // Pair token is native token, fund pool chain
            let fund_request = self.state.fund_request(transfer_id).await?;
            self.fund_pool_application_creation_chain(fund_request.amount_in);
        }

        let fund_request_0 = if let Some(transfer_id) = fund_request.prev_request {
            &self.state.fund_request(transfer_id).await?
        } else {
            fund_request
        };
        let fund_request_1 = if let Some(transfer_id) = fund_request.next_request {
            &self.state.fund_request(transfer_id).await?
        } else {
            fund_request
        };

        self.transfer_meme_to_creation_chain_application(fund_request_0);
        if let Some(_) = fund_request_1.token {
            self.transfer_meme_to_creation_chain_application(fund_request_1);
        }

        // Here both assets are transferred to pool successfully
        self.runtime
            .prepare_message(PoolMessage::AddLiquidity {
                origin: fund_request_0.from,
                amount_0_in: fund_request_0.amount_in,
                amount_1_in: fund_request_1.amount_in,
                amount_0_out_min: fund_request_0.pair_token_amount_out_min,
                amount_1_out_min: fund_request_1.pair_token_amount_out_min,
                to: fund_request_0.to,
                block_timestamp: fund_request_0.block_timestamp,
            })
            .with_authentication()
            .send_to(self.runtime.application_creator_chain_id());

        Ok(())
    }

    async fn on_msg_fund_success(&mut self, transfer_id: u64) -> Result<(), PoolError> {
        let mut fund_request = self.state.fund_request(transfer_id).await?;

        fund_request.status = FundStatus::Success;
        self.state
            .update_fund_request(transfer_id, fund_request.clone())
            .await?;

        match fund_request.fund_type {
            FundType::Swap => self.swap_fund_success(&fund_request),
            FundType::AddLiquidity => self.add_liquidity_fund_success(&fund_request).await?,
        };

        Ok(())
    }

    async fn on_msg_fund_fail(&mut self, transfer_id: u64, error: String) -> Result<(), PoolError> {
        let mut fund_request = self.state.fund_request(transfer_id).await?;

        fund_request.status = FundStatus::Fail;
        fund_request.error = Some(error);

        self.state
            .update_fund_request(transfer_id, fund_request)
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
        let call = MemeOperation::TransferToCaller { amount };

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
            _ => panic!("Invalid response"),
        };
        Ok(())
    }

    fn refund_amount_in(
        &mut self,
        origin: Account,
        amount_0_in: Option<Amount>,
        amount_1_in: Option<Amount>,
    ) {
        let amount_1_in = amount_1_in.unwrap_or(Amount::ZERO);
        if amount_1_in > Amount::ZERO {
            if let Some(token_1) = self.token_1() {
                self.transfer_meme(token_1, origin, amount_1_in);
            } else {
                let application = AccountOwner::from(self.runtime.application_id().forget_abi());
                self.runtime.transfer(application, origin, amount_1_in);
            }
        }
        let amount_0_in = amount_0_in.unwrap_or(Amount::ZERO);
        let token_0 = self.token_0();
        // Transfer native firstly due to meme transfer is a message
        if amount_0_in > Amount::ZERO {
            self.transfer_meme(token_0, origin, amount_0_in);
        }
    }

    // Always be run on creation chain
    fn do_swap(
        &mut self,
        origin: Account,
        amount_0_in: Option<Amount>,
        amount_1_in: Option<Amount>,
        amount_0_out_min: Option<Amount>,
        amount_1_out_min: Option<Amount>,
        to: Option<Account>,
        _block_timestamp: Option<Timestamp>,
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
                self.refund_amount_in(origin, amount_0_in, amount_1_in);
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
                self.refund_amount_in(origin, amount_0_in, amount_1_in);
                return Err(PoolError::InvalidAmount);
            }
        }

        if amount_0_in.unwrap_or(Amount::ZERO) > Amount::ZERO && amount_1_out == Amount::ZERO {
            self.refund_amount_in(origin, amount_0_in, amount_1_in);
            return Err(PoolError::InvalidAmount);
        }
        if amount_1_in.unwrap_or(Amount::ZERO) > Amount::ZERO && amount_0_out == Amount::ZERO {
            self.refund_amount_in(origin, amount_0_in, amount_1_in);
            return Err(PoolError::InvalidAmount);
        }
        if amount_0_out == Amount::ZERO && amount_1_out == Amount::ZERO {
            self.refund_amount_in(origin, amount_0_in, amount_1_in);
            return Err(PoolError::InvalidAmount);
        }

        // 2: Check liquidity
        match self
            .state
            .calculate_adjusted_amount_pair(amount_0_out, amount_1_out)
        {
            Ok(_) => {}
            Err(err) => {
                self.refund_amount_in(origin, amount_0_in, amount_1_in);
                return Err(err);
            }
        }

        // 3: Transfer token
        let to = to.unwrap_or(origin);
        let application = AccountOwner::from(self.runtime.application_id().forget_abi());
        let token_0 = self.token_0();

        if amount_1_out > Amount::ZERO {
            if let Some(token_1) = self.token_1() {
                self.transfer_meme(token_1, to, amount_1_out);
            } else {
                let balance = self.runtime.owner_balance(application);
                if balance < amount_1_out.try_add(open_chain_fee_budget())? {
                    self.refund_amount_in(origin, amount_0_in, amount_1_in);
                    return Err(PoolError::InsufficientFunds);
                }
                self.runtime.transfer(application, to, amount_1_out);
            }
        }
        // Transfer native firstly due to meme transfer is a message
        if amount_0_out > Amount::ZERO {
            self.transfer_meme(token_0, to, amount_0_out);
        }

        // 4: Liquid

        let balance_0 = self
            .state
            .reserve_0()
            .try_sub(amount_0_out)
            .unwrap()
            .try_add(amount_0_in.unwrap_or(Amount::ZERO))
            .unwrap();
        let balance_1 = self
            .state
            .reserve_1()
            .try_sub(amount_1_out)
            .unwrap()
            .try_add(amount_1_in.unwrap_or(Amount::ZERO))
            .unwrap();
        let timestamp = self.runtime.system_time();

        self.state.liquid(balance_0, balance_1, timestamp);

        let transaction = self.state.build_transaction(
            origin,
            amount_0_in,
            amount_1_in,
            if amount_0_out > Amount::ZERO {
                Some(amount_0_out)
            } else {
                None
            },
            if amount_1_out > Amount::ZERO {
                Some(amount_1_out)
            } else {
                None
            },
            None,
            timestamp,
        );
        // We already on creator chain
        let chain_id = self.runtime.chain_id();
        self.runtime
            .prepare_message(PoolMessage::NewTransaction { transaction })
            .with_authentication()
            .send_to(chain_id);

        Ok(())
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
        // We just return OK to refund the failed balance here
        match self.do_swap(
            origin,
            amount_0_in,
            amount_1_in,
            amount_0_out_min,
            amount_1_out_min,
            to,
            block_timestamp,
        ) {
            Ok(_) => Ok(()),
            Err(err) => {
                log::warn!("Failed swap: {}", err);
                Ok(())
            }
        }
    }

    async fn on_msg_add_liquidity(
        &mut self,
        origin: Account,
        amount_0_in: Amount,
        amount_1_in: Amount,
        amount_0_out_min: Option<Amount>,
        amount_1_out_min: Option<Amount>,
        to: Option<Account>,
        _block_timestamp: Option<Timestamp>,
    ) -> Result<(), PoolError> {
        // We already receive all funds here
        let (amount_0, amount_1) = self.state.try_calculate_swap_amount_pair(
            amount_0_in,
            amount_1_in,
            amount_0_out_min,
            amount_1_out_min,
        )?;

        let to = to.unwrap_or(origin);
        let timestamp = self.runtime.system_time();
        let liquidity = self
            .state
            .add_liquidity(amount_0, amount_1, to, timestamp)
            .await?;

        if amount_0_in > amount_0 {
            let token_0 = self.token_0();
            self.transfer_meme(token_0, origin, amount_0_in.try_sub(amount_0)?);
        }
        if amount_1_in > amount_1 {
            match self.token_1() {
                Some(token_1) => {
                    self.transfer_meme(token_1, origin, amount_1_in.try_sub(amount_1)?)
                }
                None => {
                    let application =
                        AccountOwner::from(self.runtime.application_id().forget_abi());
                    self.runtime
                        .transfer(application, origin, amount_1_in.try_sub(amount_1)?)
                }
            };
        }

        let transaction = self.state.build_transaction(
            origin,
            Some(amount_0),
            Some(amount_1),
            None,
            None,
            Some(liquidity),
            timestamp,
        );
        let chain_id = self.runtime.chain_id();
        self.runtime
            .prepare_message(PoolMessage::NewTransaction { transaction })
            .with_authentication()
            .send_to(chain_id);

        Ok(())
    }

    async fn on_msg_remove_liquidity(
        &mut self,
        origin: Account,
        liquidity: Amount,
        amount_0_out_min: Option<Amount>,
        amount_1_out_min: Option<Amount>,
        to: Option<Account>,
        _block_timestamp: Option<Timestamp>,
    ) -> Result<(), PoolError> {
        // 1: Calculate liquidity amount pair
        let (amount_0, amount_1) = self.state.try_calculate_liquidity_amount_pair(
            liquidity,
            amount_0_out_min,
            amount_1_out_min,
        )?;

        // 2: Transfer tokens
        let to = to.unwrap_or(origin);
        let token_0 = self.token_0();
        self.transfer_meme(token_0, to, amount_0);

        let application = AccountOwner::from(self.runtime.application_id().forget_abi());
        match self.token_1() {
            Some(token_1) => self.transfer_meme(token_1, to, amount_1),
            None => self.runtime.transfer(application, to, amount_1),
        };

        // 3: Burn liquidity
        self.state.burn(origin, liquidity).await?;

        let timestamp = self.runtime.system_time();
        let transaction = self.state.build_transaction(
            origin,
            None,
            None,
            Some(amount_0),
            Some(amount_1),
            Some(liquidity),
            timestamp,
        );
        let chain_id = self.runtime.chain_id();
        self.runtime
            .prepare_message(PoolMessage::NewTransaction { transaction })
            .with_authentication()
            .send_to(chain_id);

        Ok(())
    }

    fn on_msg_set_fee_to(&mut self, operator: Account, account: Account) -> Result<(), PoolError> {
        self.state.set_fee_to(operator, account);
        Ok(())
    }

    fn on_msg_set_fee_to_setter(
        &mut self,
        operator: Account,
        account: Account,
    ) -> Result<(), PoolError> {
        self.state.set_fee_to_setter(operator, account);
        Ok(())
    }

    fn on_msg_new_transaction(&mut self, transaction: Transaction) -> Result<(), PoolError> {
        // Here we got transaction id
        let transaction = self.state.create_transaction(transaction);
        let (token_0_price, token_1_price) = self.state.calculate_price_pair();
        let reserve_0 = self.state.reserve_0();
        let reserve_1 = self.state.reserve_1();

        let call = SwapOperation::UpdatePool {
            token_0: self.token_0(),
            token_1: self.token_1(),
            transaction,
            token_0_price,
            token_1_price,
            reserve_0,
            reserve_1,
        };
        let _ = self.runtime.call_application(
            true,
            self.state.router_application_id().with_abi::<SwapAbi>(),
            &call,
        );
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use abi::{
        meme::MemeResponse,
        swap::pool::{
            InstantiationArgument, PoolAbi, PoolMessage, PoolOperation, PoolParameters,
            PoolResponse,
        },
    };
    use futures::FutureExt as _;
    use linera_sdk::{
        bcs,
        linera_base_types::{Account, AccountOwner, Amount, ApplicationId, ChainId, MessageId},
        util::BlockingWait,
        views::View,
        Contract, ContractRuntime,
    };
    use pool::{FundRequest, FundStatus, FundType};
    use std::str::FromStr;

    use super::{PoolContract, PoolState};

    #[tokio::test(flavor = "multi_thread")]
    async fn create_pool_with_real_liquidity() {
        let pool = create_and_instantiate_pool(false).await;
        let _ = pool.state.pool();
    }

    #[tokio::test(flavor = "multi_thread")]
    async fn create_pool_with_virtual_liquidity() {
        let pool = create_and_instantiate_pool(true).await;
        let _ = pool.state.pool();
    }

    #[tokio::test(flavor = "multi_thread")]
    async fn operation_swap() {
        let mut pool = create_and_instantiate_pool(true).await;

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
    async fn operation_add_liquidity() {
        let mut pool = create_and_instantiate_pool(true).await;

        let response = pool
            .execute_operation(PoolOperation::AddLiquidity {
                amount_0_in: Amount::ONE,
                amount_1_in: Amount::from_tokens(20),
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
        let mut pool = create_and_instantiate_pool(true).await;

        pool.execute_message(PoolMessage::RequestFund {
            token: pool.state.pool().token_0,
            transfer_id: 1000,
            amount: Amount::ONE,
        })
        .await;
    }

    #[tokio::test(flavor = "multi_thread")]
    async fn message_fund_success() {
        let mut pool = create_and_instantiate_pool(true).await;
        let owner = Account {
            chain_id: pool.runtime.chain_id(),
            owner: pool.runtime.authenticated_signer().unwrap(),
        };

        let fund_request = FundRequest {
            from: owner,
            token: Some(pool.token_0()),
            amount_in: Amount::ONE,
            pair_token_amount_out_min: None,
            to: None,
            block_timestamp: None,
            fund_type: FundType::Swap,
            status: FundStatus::InFlight,
            error: None,
            prev_request: None,
            next_request: None,
        };

        let transfer_id = pool.state.create_fund_request(fund_request).unwrap();
        pool.execute_message(PoolMessage::FundSuccess { transfer_id })
            .await;

        let fund_request = pool.state.fund_request(transfer_id).await.unwrap();
        assert_eq!(fund_request.status, FundStatus::Success);
    }

    #[tokio::test(flavor = "multi_thread")]
    async fn message_fund_fail() {
        let mut pool = create_and_instantiate_pool(true).await;
        let owner = Account {
            chain_id: pool.runtime.chain_id(),
            owner: pool.runtime.authenticated_signer().unwrap(),
        };

        let fund_request = FundRequest {
            from: owner,
            token: Some(pool.token_0()),
            amount_in: Amount::ONE,
            pair_token_amount_out_min: None,
            to: None,
            block_timestamp: None,
            fund_type: FundType::Swap,
            status: FundStatus::InFlight,
            error: None,
            prev_request: None,
            next_request: None,
        };

        let transfer_id = pool.state.create_fund_request(fund_request).unwrap();
        pool.execute_message(PoolMessage::FundFail {
            transfer_id,
            error: "Error".to_string(),
        })
        .await;

        let fund_request = pool.state.fund_request(transfer_id).await.unwrap();
        assert_eq!(fund_request.status, FundStatus::Fail);
        assert_eq!(fund_request.error, Some("Error".to_string()));
    }

    #[tokio::test(flavor = "multi_thread")]
    async fn message_swap() {
        let mut pool = create_and_instantiate_pool(true).await;
        let owner = Account {
            chain_id: pool.runtime.chain_id(),
            owner: pool.runtime.authenticated_signer().unwrap(),
        };

        let reserve_0 = pool.state.reserve_0();
        let reserve_1 = pool.state.reserve_1();
        let swap_amount_0 = pool.state.calculate_swap_amount_0(Amount::ONE).unwrap();

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

        assert_eq!(
            reserve_0.try_sub(swap_amount_0).unwrap(),
            pool.state.reserve_0()
        );
        assert_eq!(
            reserve_1.try_add(Amount::ONE).unwrap(),
            pool.state.reserve_1()
        );
    }

    #[tokio::test(flavor = "multi_thread")]
    async fn message_add_liquidity() {
        let mut pool = create_and_instantiate_pool(true).await;
        let owner = Account {
            chain_id: pool.runtime.chain_id(),
            owner: pool.runtime.authenticated_signer().unwrap(),
        };

        pool.execute_message(PoolMessage::AddLiquidity {
            origin: owner,
            amount_0_in: Amount::ONE,
            amount_1_in: Amount::from_tokens(10),
            amount_0_out_min: None,
            amount_1_out_min: None,
            to: None,
            block_timestamp: None,
        })
        .await;

        assert_eq!(
            pool.state.liquidity(owner).await.unwrap(),
            Amount::from_str("0.1").unwrap()
        );

        pool.execute_message(PoolMessage::RemoveLiquidity {
            origin: owner,
            liquidity: Amount::from_str("0.05").unwrap(),
            amount_0_out_min: None,
            amount_1_out_min: None,
            to: None,
            block_timestamp: None,
        })
        .await;

        assert_eq!(
            pool.state.liquidity(owner).await.unwrap(),
            Amount::from_str("0.05").unwrap()
        );
    }

    #[test]
    fn cross_application_call() {}

    fn mock_application_call(
        _authenticated: bool,
        _application_id: ApplicationId,
        _operation: Vec<u8>,
    ) -> Vec<u8> {
        bcs::to_bytes(&MemeResponse::Ok).unwrap()
    }

    async fn create_and_instantiate_pool(virtual_initial_liquidity: bool) -> PoolContract {
        let _ = env_logger::builder().is_test(true).try_init();

        let token_0 = ApplicationId::from_str(
            "b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bad",
        )
        .unwrap();
        let token_1 = ApplicationId::from_str(
            "b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bae",
        )
        .unwrap();
        let router_application_id = ApplicationId::from_str(
            "b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5baf",
        )
        .unwrap();
        let chain_id =
            ChainId::from_str("aee928d4bf3880353b4a3cd9b6f88e6cc6e5ed050860abae439e7782e9b2dfe8")
                .unwrap();
        let application_id = ApplicationId::from_str(
            "b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bbd",
        )
        .unwrap()
        .with_abi::<PoolAbi>();
        let owner = AccountOwner::from_str(
            "0x5279b3ae14d3b38e14b65a74aefe44824ea88b25c7841836e9ec77d991a5bc7f",
        )
        .unwrap();
        let creator = Account { chain_id, owner };
        let message_id = MessageId::from_str("dad01517c7a3c428ea903253a9e59964e8db06d323a9bd3f4c74d6366832bdbf801200000000000000000000").unwrap();
        let runtime = ContractRuntime::new()
            .with_application_parameters(PoolParameters {
                creator,
                token_0,
                token_1: Some(token_1),
                virtual_initial_liquidity,
                token_0_creator_chain_id: chain_id,
                token_1_creator_chain_id: Some(chain_id),
            })
            .with_chain_id(chain_id)
            .with_application_id(application_id)
            .with_authenticated_caller_id(router_application_id)
            .with_call_application_handler(mock_application_call)
            .with_application_creator_chain_id(chain_id)
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
            .await;

        contract
    }
}
