// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

#![cfg_attr(target_arch = "wasm32", no_main)]

mod state;

use abi::{
    constant::OPEN_CHAIN_FEE_BUDGET,
    meme::{MemeAbi, MemeOperation},
    swap::{
        liquidity_rfq::{LiquidityRfqAbi, LiquidityRfqParameters},
        pool::{InstantiationArgument as PoolInstantiationArgument, PoolAbi, PoolParameters},
        router::{
            InstantiationArgument, SwapAbi, SwapMessage, SwapOperation, SwapParameters,
            SwapResponse,
        },
    },
};
use linera_sdk::{
    linera_base_types::{
        Account, AccountOwner, Amount, ApplicationId, ApplicationPermissions, ChainId, MessageId,
        ModuleId, Timestamp, WithContractAbi,
    },
    views::{RootView, View},
    Contract, ContractRuntime,
};
use swap::SwapError;

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
    type Message = SwapMessage;
    type InstantiationArgument = InstantiationArgument;
    type Parameters = SwapParameters;

    async fn load(runtime: ContractRuntime<Self>) -> Self {
        let state = SwapState::load(runtime.root_view_storage_context())
            .await
            .expect("Failed to load state");
        SwapContract { state, runtime }
    }

    async fn instantiate(&mut self, argument: InstantiationArgument) {
        // Validate that the application parameters were configured correctly.
        self.runtime.application_parameters();

        self.state.instantiate(argument).await;
    }

    async fn execute_operation(&mut self, operation: SwapOperation) -> SwapResponse {
        match operation {
            SwapOperation::InitializeLiquidity {
                token_0,
                amount_0,
                amount_1,
                // Only for creator to initialize pool
                virtual_liquidity,
                to,
            } => self
                .on_call_initialize_liquidity(token_0, amount_0, amount_1, virtual_liquidity, to)
                .await
                .expect("Failed OP: initialize liquidity"),
            SwapOperation::AddLiquidity {
                token_0,
                token_1,
                amount_0_desired,
                amount_1_desired,
                amount_0_min,
                amount_1_min,
                to,
                deadline,
            } => self
                .on_op_add_liquidity(
                    token_0,
                    token_1,
                    amount_0_desired,
                    amount_1_desired,
                    amount_0_min,
                    amount_1_min,
                    to,
                    deadline,
                )
                .await
                .expect("Failed OP: add liquidity"),
            SwapOperation::LiquidityFundApproved {
                token_0,
                token_1,
                amount_0_desired,
                amount_1_desired,
                amount_0_min,
                amount_1_min,
                to,
                deadline,
            } => self
                .on_op_liquidity_fund_approved(
                    token_0,
                    token_1,
                    amount_0_desired,
                    amount_1_desired,
                    amount_0_min,
                    amount_1_min,
                    to,
                    deadline,
                )
                .expect("Failed OP: liquidity fund approved"),
            SwapOperation::RemoveLiquidity {
                token_0,
                token_1,
                liquidity,
                amount_0_min,
                amount_1_min,
                to,
                deadline,
            } => self
                .on_op_remove_liquidity(
                    token_0,
                    token_1,
                    liquidity,
                    amount_0_min,
                    amount_1_min,
                    to,
                    deadline,
                )
                .expect("Failed OP: remove liquidity"),
            SwapOperation::Swap {
                token_0,
                token_1,
                amount_0_in,
                amount_1_in,
                amount_0_out_min,
                amount_1_out_min,
                to,
                deadline,
            } => self
                .on_op_swap(
                    token_0,
                    token_1,
                    amount_0_in,
                    amount_1_in,
                    amount_0_out_min,
                    amount_1_out_min,
                    to,
                    deadline,
                )
                .expect("Failed OP: swap"),
        }
    }

    async fn execute_message(&mut self, message: SwapMessage) {
        // All messages must be run on creation chain side
        if !self.message_executable(&message) {
            panic!("Messages must only be run on right chain");
        }

        match message {
            SwapMessage::InitializeLiquidity {
                token_0,
                amount_0,
                amount_1,
                // Only for creator to initialize pool
                virtual_liquidity,
                to,
            } => self
                .on_msg_initialize_liquidity(token_0, amount_0, amount_1, virtual_liquidity, to)
                .await
                .expect("Failed MSG: initialize liquidity"),
            SwapMessage::AddLiquidity {
                token_0,
                token_1,
                amount_0_desired,
                amount_1_desired,
                amount_0_min,
                amount_1_min,
                to,
                deadline,
            } => self
                .on_msg_add_liquidity(
                    token_0,
                    token_1,
                    amount_0_desired,
                    amount_1_desired,
                    amount_0_min,
                    amount_1_min,
                    to,
                    deadline,
                )
                .await
                .expect("Failed MSG: add liquidity"),
            SwapMessage::CreateRfq {
                rfq_bytecode_id,
                token_0,
                token_1,
                amount_0,
                amount_1,
            } => self
                .on_msg_create_rfq(rfq_bytecode_id, token_0, token_1, amount_0, amount_1)
                .expect("Failed MSG: create rfq"),
            SwapMessage::CreatePool {
                pool_bytecode_id,
                token_0,
                token_1,
                amount_0,
                amount_1,
                virtual_initial_liquidity,
            } => self
                .on_msg_create_pool(
                    pool_bytecode_id,
                    token_0,
                    token_1,
                    amount_0,
                    amount_1,
                    virtual_initial_liquidity,
                )
                .expect("Failed MSG: create pool"),
            SwapMessage::PoolCreated {
                pool_application,
                token_0,
                token_1,
                amount_0,
                amount_1,
                virtual_initial_liquidity,
            } => self
                .on_msg_pool_created(
                    pool_application,
                    token_0,
                    token_1,
                    amount_0,
                    amount_1,
                    virtual_initial_liquidity,
                )
                .await
                .expect("Failed MSG: pool created"),
            SwapMessage::LiquidityFundApproved {
                token_0,
                token_1,
                amount_0_desired,
                amount_1_desired,
                amount_0_min,
                amount_1_min,
                to,
                deadline,
            } => self
                .on_msg_liquidity_fund_approved(
                    token_0,
                    token_1,
                    amount_0_desired,
                    amount_1_desired,
                    amount_0_min,
                    amount_1_min,
                    to,
                    deadline,
                )
                .await
                .expect("Failed MSG: liquidity fund approved"),
            SwapMessage::RemoveLiquidity {
                token_0,
                token_1,
                liquidity,
                amount_0_min,
                amount_1_min,
                to,
                deadline,
            } => self
                .on_msg_remove_liquidity(
                    token_0,
                    token_1,
                    liquidity,
                    amount_0_min,
                    amount_1_min,
                    to,
                    deadline,
                )
                .await
                .expect("Failed MSG: remove liquidity"),
            SwapMessage::Swap {
                token_0,
                token_1,
                amount_0_in,
                amount_1_in,
                amount_0_out_min,
                amount_1_out_min,
                to,
                deadline,
            } => self
                .on_msg_swap(
                    token_0,
                    token_1,
                    amount_0_in,
                    amount_1_in,
                    amount_0_out_min,
                    amount_1_out_min,
                    to,
                    deadline,
                )
                .await
                .expect("Failed MSG: swap"),
        }
    }

    async fn store(mut self) {
        self.state.save().await.expect("Failed to save state");
    }
}

impl SwapContract {
    fn message_executable(&mut self, message: &SwapMessage) -> bool {
        match message {
            SwapMessage::CreateRfq { .. } | SwapMessage::CreatePool { .. } => {
                self.runtime.chain_id() != self.runtime.application_id().creation.chain_id
            }
            _ => self.runtime.chain_id() == self.runtime.application_id().creation.chain_id,
        }
    }

    fn formalize_virtual_liquidity(
        &mut self,
        token_0: ApplicationId,
        token_1: Option<ApplicationId>,
        virtual_liquidity: bool,
    ) -> bool {
        if !virtual_liquidity {
            return false;
        }
        if token_1.is_some() {
            return false;
        }

        let Some(caller_application_id) = self.runtime.authenticated_caller_id() else {
            return false;
        };
        if caller_application_id != token_0 {
            return false;
        }
        if self.runtime.chain_id() != token_0.creation.chain_id {
            return false;
        }
        return true;
    }

    fn create_child_chain(
        &mut self,
        token_0: ApplicationId,
        token_1: Option<ApplicationId>,
    ) -> Result<(MessageId, ChainId), SwapError> {
        // It should allow router and meme applications
        let ownership = self.runtime.chain_ownership();

        let router_application_id = self.runtime.application_id().forget_abi();
        let mut application_ids = vec![token_0, router_application_id];
        if let Some(token_1) = token_1 {
            application_ids.push(token_1);
        }

        let permissions = ApplicationPermissions {
            execute_operations: Some(application_ids),
            mandatory_applications: vec![],
            close_chain: vec![router_application_id],
            change_application_permissions: vec![router_application_id],
        };
        Ok(self
            .runtime
            .open_chain(ownership, permissions, OPEN_CHAIN_FEE_BUDGET))
    }

    async fn request_liquidity_funds(
        &mut self,
        token_0: ApplicationId,
        token_1: Option<ApplicationId>,
        amount_0: Amount,
        amount_1: Amount,
    ) -> Result<(), SwapError> {
        // 1: Create rfq chain
        let (message_id, chain_id) = self.create_child_chain(token_0, token_1)?;
        // 2: Create rfq application
        let bytecode_id = self.state.liquidity_rfq_bytecode_id().await;

        self.runtime
            .prepare_message(SwapMessage::CreateRfq {
                rfq_bytecode_id: bytecode_id,
                token_0,
                token_1,
                amount_0,
                amount_1,
            })
            .with_authentication()
            .send_to(chain_id);

        Ok(())
    }

    fn fund_swap_creation_chain(
        &mut self,
        from_owner: AccountOwner,
        to_owner: Option<AccountOwner>,
        amount: Amount,
    ) {
        let chain_id = self.runtime.application_id().creation.chain_id;
        let application_id = self.runtime.application_id().forget_abi();

        let owner_balance = self.runtime.owner_balance(from_owner);
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

        // TODO: should we transfer to swap application directly ? SECURITY
        if from_owner_balance > Amount::ZERO {
            self.runtime.transfer(
                Some(from_owner),
                Account {
                    chain_id,
                    owner: to_owner,
                },
                from_owner_balance,
            );
        }
        if from_chain_balance > Amount::ZERO {
            self.runtime.transfer(
                None,
                Account {
                    chain_id,
                    owner: to_owner,
                },
                from_chain_balance,
            );
        }
    }

    async fn on_call_initialize_liquidity(
        &mut self,
        token_0: ApplicationId,
        amount_0: Amount,
        amount_1: Amount,
        virtual_liquidity: bool,
        to: Option<AccountOwner>,
    ) -> Result<SwapResponse, SwapError> {
        let caller_id = self.runtime.authenticated_caller_id().unwrap();
        let chain_id = self.runtime.chain_id();

        assert!(token_0 == caller_id, "Invalid caller");
        assert!(chain_id == caller_id.creation.chain_id, "Invalid caller");

        let virtual_liquidity = self.formalize_virtual_liquidity(token_0, None, virtual_liquidity);

        // Here allowance is already approved, so just transfer native amount then create pool
        // chain and application
        // This call should always be from token application on creation chain, and the funds is already deposit to swap application of current chain
        // We cannot transfer from meme application here due to security restrict. We must transfer
        // to swap application of current chain then transfer to swap application creation chain to
        // add liquidity
        let application = AccountOwner::Application(self.runtime.application_id().forget_abi());
        self.fund_swap_creation_chain(application, None, OPEN_CHAIN_FEE_BUDGET);
        if !virtual_liquidity {
            self.fund_swap_creation_chain(application, Some(application), amount_1);
        }

        self.runtime
            .prepare_message(SwapMessage::InitializeLiquidity {
                token_0,
                amount_0,
                amount_1,
                virtual_liquidity,
                to,
            })
            .with_authentication()
            .send_to(self.runtime.application_id().creation.chain_id);

        Ok(SwapResponse::Ok)
    }

    async fn on_op_add_liquidity(
        &mut self,
        token_0: ApplicationId,
        token_1: Option<ApplicationId>,
        amount_0_desired: Amount,
        amount_1_desired: Amount,
        amount_0_min: Amount,
        amount_1_min: Amount,
        to: Option<AccountOwner>,
        deadline: Option<Timestamp>,
    ) -> Result<SwapResponse, SwapError> {
        // TODO: transfer liquidity amount

        self.runtime
            .prepare_message(SwapMessage::AddLiquidity {
                token_0,
                token_1,
                amount_0_desired,
                amount_1_desired,
                amount_0_min,
                amount_1_min,
                to,
                deadline,
            })
            .with_authentication()
            .send_to(self.runtime.application_id().creation.chain_id);

        Ok(SwapResponse::Ok)
    }

    fn on_op_liquidity_fund_approved(
        &mut self,
        token_0: ApplicationId,
        token_1: Option<ApplicationId>,
        amount_0_desired: Amount,
        amount_1_desired: Amount,
        amount_0_min: Amount,
        amount_1_min: Amount,
        to: Option<AccountOwner>,
        deadline: Option<Timestamp>,
    ) -> Result<SwapResponse, SwapError> {
        Ok(SwapResponse::Ok)
    }

    fn on_op_remove_liquidity(
        &mut self,
        token_0: ApplicationId,
        token_1: Option<ApplicationId>,
        liquidity: Amount,
        amount_0_min: Amount,
        amount_1_min: Amount,
        to: Option<AccountOwner>,
        deadline: Option<Timestamp>,
    ) -> Result<SwapResponse, SwapError> {
        Ok(SwapResponse::Ok)
    }

    fn on_op_swap(
        &mut self,
        token_0: ApplicationId,
        token_1: Option<ApplicationId>,
        amount_0_in: Option<Amount>,
        amount_1_in: Option<Amount>,
        amount_0_out_min: Option<Amount>,
        amount_1_out_min: Option<Amount>,
        to: Option<AccountOwner>,
        deadline: Option<Timestamp>,
    ) -> Result<SwapResponse, SwapError> {
        Ok(SwapResponse::Ok)
    }

    fn pool_chain_add_liquidity(
        &mut self,
        pool_application: Account,
        amount_0_desired: Amount,
        amount_1_desired: Amount,
        amount_0_min: Amount,
        amount_1_min: Amount,
        to: Option<AccountOwner>,
        deadline: Option<Timestamp>,
    ) -> Result<(), SwapError> {
        // 1: Call pool application to add liquidity
        Ok(())
    }

    // Pool application is run on its own chain
    async fn create_pool(
        &mut self,
        token_0: ApplicationId,
        token_1: Option<ApplicationId>,
        amount_0: Amount,
        amount_1: Amount,
        virtual_liquidity: bool,
        to: Option<AccountOwner>,
        deadline: Option<Timestamp>,
    ) -> Result<(), SwapError> {
        // All assets should be already authenticated when we're here
        // 1: Create pool chain
        let (message_id, chain_id) = self.create_child_chain(token_0, token_1)?;
        self.state.create_pool_chain(chain_id, message_id).await?;
        // 2: Create pool application with initial liquidity
        let bytecode_id = self.state.pool_bytecode_id().await;

        self.runtime
            .prepare_message(SwapMessage::CreatePool {
                pool_bytecode_id: bytecode_id,
                token_0,
                token_1,
                amount_0,
                amount_1,
                virtual_initial_liquidity: virtual_liquidity,
            })
            .with_authentication()
            .send_to(chain_id);

        // Assets will be transfer to pool chain when create pool application
        Ok(())
    }

    async fn on_msg_initialize_liquidity(
        &mut self,
        token_0: ApplicationId,
        amount_0: Amount,
        amount_1: Amount,
        virtual_liquidity: bool,
        to: Option<AccountOwner>,
    ) -> Result<(), SwapError> {
        self.create_pool(
            token_0,
            None,
            amount_0,
            amount_1,
            virtual_liquidity,
            to,
            None,
        )
        .await
    }

    async fn on_msg_add_liquidity(
        &mut self,
        token_0: ApplicationId,
        token_1: Option<ApplicationId>,
        amount_0_desired: Amount,
        amount_1_desired: Amount,
        amount_0_min: Amount,
        amount_1_min: Amount,
        to: Option<AccountOwner>,
        deadline: Option<Timestamp>,
    ) -> Result<(), SwapError> {
        // Request liquidity funds in rfq chain
        // If success, rfq application will call LiquidityFundApproved then we can create pool or
        // add liquidity
        Ok(self
            .request_liquidity_funds(token_0, token_1, amount_0_desired, amount_1_desired)
            .await?)
    }

    fn on_msg_create_rfq(
        &mut self,
        rfq_bytecode_id: ModuleId,
        token_0: ApplicationId,
        token_1: Option<ApplicationId>,
        amount_0: Amount,
        amount_1: Amount,
    ) -> Result<(), SwapError> {
        // Run on rfq chain
        let application_id = self.runtime.application_id().forget_abi();

        let _ = self
            .runtime
            .create_application::<LiquidityRfqAbi, LiquidityRfqParameters, ()>(
                rfq_bytecode_id,
                &LiquidityRfqParameters {
                    token_0,
                    token_1,
                    amount_0,
                    amount_1,
                    router_application_id: application_id,
                },
                &(),
                vec![],
            );

        Ok(())
    }

    fn on_msg_create_pool(
        &mut self,
        pool_bytecode_id: ModuleId,
        token_0: ApplicationId,
        token_1: Option<ApplicationId>,
        amount_0: Amount,
        amount_1: Amount,
        virtual_initial_liquidity: bool,
    ) -> Result<(), SwapError> {
        // Run on pool chain
        let application_id = self.runtime.application_id().forget_abi();
        let chain_id = self.runtime.chain_id();

        let pool_application_id = self
            .runtime
            .create_application::<PoolAbi, PoolParameters, PoolInstantiationArgument>(
                pool_bytecode_id,
                &PoolParameters {
                    token_0,
                    token_1,
                    router_application_id: application_id,
                },
                &PoolInstantiationArgument { amount_0, amount_1 },
                vec![],
            )
            .forget_abi();

        // Here we're on meme chain, we should goto swap chain to transfer funds due to we deposit
        // there
        let pool_application = Account {
            chain_id,
            owner: Some(AccountOwner::Application(pool_application_id)),
        };
        self.runtime
            .prepare_message(SwapMessage::PoolCreated {
                pool_application,
                token_0,
                token_1,
                amount_0,
                amount_1,
                virtual_initial_liquidity,
            })
            .with_authentication()
            .send_to(application_id.creation.chain_id);

        Ok(())
    }

    async fn on_msg_pool_created(
        &mut self,
        pool_application: Account,
        token_0: ApplicationId,
        token_1: Option<ApplicationId>,
        amount_0: Amount,
        amount_1: Amount,
        virtual_initial_liquidity: bool,
    ) -> Result<(), SwapError> {
        assert!(amount_1 > Amount::ZERO, "Invalid amount");
        assert!(amount_0 > Amount::ZERO, "Invalid amount");

        if let Some(token_1) = token_1 {
            panic!("Not supported pair with meme");
        } else if !virtual_initial_liquidity {
            // This message may be authenticated by other user who is not the owner of swap
            // creation chain
            let application = AccountOwner::Application(self.runtime.application_id().forget_abi());
            self.runtime
                .transfer(Some(application), pool_application, amount_1);
        }

        // TODO: only call from InitializeLiquidity could transfer from application
        let call = MemeOperation::TransferFromApplication {
            to: pool_application,
            amount: amount_0,
        };
        let _ = self
            .runtime
            .call_application(true, token_0.with_abi::<MemeAbi>(), &call);

        self.state
            .create_pool(token_0, token_1, pool_application)
            .await
    }

    async fn on_msg_liquidity_fund_approved(
        &mut self,
        token_0: ApplicationId,
        token_1: Option<ApplicationId>,
        amount_0_desired: Amount,
        amount_1_desired: Amount,
        amount_0_min: Amount,
        amount_1_min: Amount,
        to: Option<AccountOwner>,
        deadline: Option<Timestamp>,
    ) -> Result<(), SwapError> {
        // Fund is ready, create liquidity pool
        if let Some(pool) = self.state.get_pool_exchangable(token_0, token_1).await? {
            self.pool_chain_add_liquidity(
                pool.pool_application,
                if pool.token_0 == token_0 {
                    amount_0_desired
                } else {
                    amount_1_desired
                },
                if pool.token_0 == token_0 {
                    amount_1_desired
                } else {
                    amount_0_desired
                },
                if pool.token_0 == token_0 {
                    amount_0_min
                } else {
                    amount_1_min
                },
                if pool.token_0 == token_0 {
                    amount_1_min
                } else {
                    amount_0_min
                },
                to,
                deadline,
            )
        } else {
            self.create_pool(
                token_0,
                token_1,
                amount_0_desired,
                amount_1_desired,
                false,
                to,
                deadline,
            )
            .await
        }
    }

    async fn on_msg_remove_liquidity(
        &mut self,
        token_0: ApplicationId,
        token_1: Option<ApplicationId>,
        liquidity: Amount,
        amount_0_min: Amount,
        amount_1_min: Amount,
        to: Option<AccountOwner>,
        deadline: Option<Timestamp>,
    ) -> Result<(), SwapError> {
        Ok(())
    }

    async fn on_msg_swap(
        &mut self,
        token_0: ApplicationId,
        token_1: Option<ApplicationId>,
        amount_0_in: Option<Amount>,
        amount_1_in: Option<Amount>,
        amount_0_out_min: Option<Amount>,
        amount_1_out_min: Option<Amount>,
        to: Option<AccountOwner>,
        deadline: Option<Timestamp>,
    ) -> Result<(), SwapError> {
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use abi::swap::router::{
        InstantiationArgument, SwapAbi, SwapOperation, SwapParameters, SwapResponse,
    };
    use futures::FutureExt as _;
    use linera_sdk::{
        linera_base_types::{
            AccountOwner, Amount, ApplicationId, ApplicationPermissions, ChainOwnership, MessageId,
            ModuleId, Owner,
        },
        util::BlockingWait,
        views::View,
        Contract, ContractRuntime,
    };
    use std::str::FromStr;

    use super::{SwapContract, SwapState};

    #[tokio::test(flavor = "multi_thread")]
    async fn operation_initialize_liquidity() {
        let mut swap = create_and_instantiate_swap();

        let meme_1_id = "b94e486abcfc016e937dad4297523060095f405530c95d498d981a94141589f167693295a14c3b48460ad6f75d67d2414428227550eb8cee8ecaa37e8646518300aee928d4bf3880353b4a3cd9b6f88e6cc6e5ed050860abae439e7782e9b2dfe8020000000000000000000008";
        let meme_1 = ApplicationId::from_str(meme_1_id).unwrap();

        let response = swap
            .execute_operation(SwapOperation::InitializeLiquidity {
                token_0: meme_1,
                amount_0: Amount::ONE,
                amount_1: Amount::ONE,
                virtual_liquidity: false,
                to: None,
            })
            .await;

        assert!(matches!(response, SwapResponse::Ok));
    }

    #[tokio::test(flavor = "multi_thread")]
    async fn operation_add_liquidity() {
        let mut swap = create_and_instantiate_swap();

        let meme_1_id = "b94e486abcfc016e937dad4297523060095f405530c95d498d981a94141589f167693295a14c3b48460ad6f75d67d2414428227550eb8cee8ecaa37e8646518300aee928d4bf3880353b4a3cd9b6f88e6cc6e5ed050860abae439e7782e9b2dfe8020000000000000000000008";
        let meme_1 = ApplicationId::from_str(meme_1_id).unwrap();

        let response = swap
            .execute_operation(SwapOperation::AddLiquidity {
                token_0: meme_1,
                token_1: None,
                amount_0_desired: Amount::ONE,
                amount_1_desired: Amount::ONE,
                amount_0_min: Amount::ONE,
                amount_1_min: Amount::ONE,
                to: None,
                deadline: None,
            })
            .await;

        assert!(matches!(response, SwapResponse::Ok));
    }

    #[test]
    fn message() {}

    #[test]
    fn cross_application_call() {}

    fn create_and_instantiate_swap() -> SwapContract {
        let owner =
            Owner::from_str("02e900512d2fca22897f80a2f6932ff454f2752ef7afad18729dd25e5b5b6e00")
                .unwrap();
        let application_id_str = "b94e486abcfc016e937dad4297523060095f405530c95d498d981a94141589f167693295a14c3b48460ad6f75d67d2414428227550eb8cee8ecaa37e8646518300aee928d4bf3880353b4a3cd9b6f88e6cc6e5ed050860abae439e7782e9b2dfe8020000000000000000000000";
        let application_id = ApplicationId::from_str(application_id_str)
            .unwrap()
            .with_abi::<SwapAbi>();
        let message_id = MessageId::from_str("dad01517c7a3c428ea903253a9e59964e8db06d323a9bd3f4c74d6366832bdbf801200000000000000000000").unwrap();
        let meme_1_id = "b94e486abcfc016e937dad4297523060095f405530c95d498d981a94141589f167693295a14c3b48460ad6f75d67d2414428227550eb8cee8ecaa37e8646518300aee928d4bf3880353b4a3cd9b6f88e6cc6e5ed050860abae439e7782e9b2dfe8020000000000000000000008";
        let meme_1 = ApplicationId::from_str(meme_1_id).unwrap();

        let mut runtime = ContractRuntime::new()
            .with_application_parameters(SwapParameters {})
            .with_application_id(application_id)
            .with_authenticated_signer(owner)
            .with_authenticated_caller_id(meme_1)
            .with_chain_id(meme_1.creation.chain_id)
            .with_owner_balance(AccountOwner::User(owner), Amount::from_tokens(10000))
            .with_owner_balance(
                AccountOwner::Application(application_id.forget_abi()),
                Amount::from_tokens(10000),
            )
            .with_chain_balance(Amount::from_tokens(10000))
            .with_chain_ownership(ChainOwnership::single(owner));

        let permissions = ApplicationPermissions {
            execute_operations: Some(vec![meme_1, application_id.forget_abi()]),
            mandatory_applications: vec![],
            close_chain: vec![application_id.forget_abi()],
            change_application_permissions: vec![application_id.forget_abi()],
        };

        runtime.add_expected_open_chain_call(
            ChainOwnership::single(owner),
            permissions,
            Amount::from_tokens(1),
            message_id,
        );

        let mut contract = SwapContract {
            state: SwapState::load(runtime.root_view_storage_context())
                .blocking_wait()
                .expect("Failed to read from mock key value store"),
            runtime,
        };

        let bytecode_id = ModuleId::from_str("b94e486abcfc016e937dad4297523060095f405530c95d498d981a94141589f167693295a14c3b48460ad6f75d67d2414428227550eb8cee8ecaa37e8646518300").unwrap();
        contract
            .instantiate(InstantiationArgument {
                liquidity_rfq_bytecode_id: bytecode_id,
                pool_bytecode_id: bytecode_id,
            })
            .now_or_never()
            .expect("Initialization of swap state should not await anything");

        assert_eq!(
            *contract
                .state
                .liquidity_rfq_bytecode_id
                .get()
                .as_ref()
                .unwrap(),
            bytecode_id,
        );

        contract
    }
}
