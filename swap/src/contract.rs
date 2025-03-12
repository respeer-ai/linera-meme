// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

#![cfg_attr(target_arch = "wasm32", no_main)]

mod state;

use abi::{
    constant::OPEN_CHAIN_FEE_BUDGET,
    meme::{MemeAbi, MemeOperation},
    swap::{
        pool::{
            InstantiationArgument as PoolInstantiationArgument, PoolAbi, PoolOperation,
            PoolParameters,
        },
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
                token_0_creator_chain_id,
                token_0,
                amount_0,
                amount_1,
                // Only for creator to initialize pool
                virtual_liquidity,
                to,
            } => self
                .on_call_initialize_liquidity(
                    token_0_creator_chain_id,
                    token_0,
                    amount_0,
                    amount_1,
                    virtual_liquidity,
                    to,
                )
                .await
                .expect("Failed OP: initialize liquidity"),
            SwapOperation::CreatePool {
                token_0,
                token_1,
                amount_0,
                amount_1,
                to,
            } => self
                .on_op_create_pool(token_0, token_1, amount_0, amount_1, to)
                .await
                .expect("Failed OP: create pool"),
        }
    }

    async fn execute_message(&mut self, message: SwapMessage) {
        // All messages must be run on creation chain side
        if !self.message_executable(&message) {
            panic!("Messages must only be run on right chain");
        }

        match message {
            SwapMessage::InitializeLiquidity {
                token_0_creator_chain_id,
                token_0,
                amount_0,
                amount_1,
                // Only for creator to initialize pool
                virtual_liquidity,
                to,
            } => self
                .on_msg_initialize_liquidity(
                    token_0_creator_chain_id,
                    token_0,
                    amount_0,
                    amount_1,
                    virtual_liquidity,
                    to,
                )
                .await
                .expect("Failed MSG: initialize liquidity"),
            SwapMessage::CreatePool {
                creator,
                pool_bytecode_id,
                token_0_creator_chain_id,
                token_0,
                token_1_creator_chain_id,
                token_1,
                amount_0,
                amount_1,
                virtual_initial_liquidity,
                to,
            } => self
                .on_msg_create_pool(
                    creator,
                    pool_bytecode_id,
                    token_0_creator_chain_id,
                    token_0,
                    token_1_creator_chain_id,
                    token_1,
                    amount_0,
                    amount_1,
                    virtual_initial_liquidity,
                    to,
                )
                .expect("Failed MSG: create pool"),
            SwapMessage::PoolCreated {
                creator,
                pool_application,
                token_0,
                token_1,
                amount_0,
                amount_1,
                virtual_initial_liquidity,
                to,
            } => self
                .on_msg_pool_created(
                    creator,
                    pool_application,
                    token_0,
                    token_1,
                    amount_0,
                    amount_1,
                    virtual_initial_liquidity,
                    to,
                )
                .await
                .expect("Failed MSG: pool created"),
            SwapMessage::CreateUserPool {
                token_0,
                token_1,
                amount_0,
                amount_1,
                to,
            } => self
                .on_msg_create_user_pool(token_0, token_1, amount_0, amount_1, to)
                .await
                .expect("Failed MSG: create user pool"),
            SwapMessage::UserPoolCreated {
                pool_application,
                token_0,
                token_1,
                amount_0,
                amount_1,
                to,
            } => self
                .on_msg_user_pool_created(
                    pool_application,
                    token_0,
                    token_1,
                    amount_0,
                    amount_1,
                    to,
                )
                .await
                .expect("Failed MSG: user pool created"),
        }
    }

    async fn store(mut self) {
        self.state.save().await.expect("Failed to save state");
    }
}

impl SwapContract {
    fn message_executable(&mut self, message: &SwapMessage) -> bool {
        match message {
            SwapMessage::CreatePool { .. } => {
                self.runtime.chain_id() != self.runtime.application_creator_chain_id()
            }
            _ => self.runtime.chain_id() == self.runtime.application_creator_chain_id(),
        }
    }

    fn formalize_virtual_liquidity(
        &mut self,
        token_0_creator_chain_id: ChainId,
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
        // Here we cannot call to meme application for creator chain id due to it's called from
        // meme application.
        if self.runtime.chain_id() != token_0_creator_chain_id {
            return false;
        }
        return true;
    }

    fn message_owner_account(&mut self) -> Account {
        Account {
            chain_id: self.runtime.message_id().unwrap().chain_id,
            owner: Some(AccountOwner::User(
                self.runtime.authenticated_signer().unwrap(),
            )),
        }
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

    fn fund_swap_creation_chain(
        &mut self,
        from_owner: AccountOwner,
        to_owner: Option<AccountOwner>,
        amount: Amount,
    ) {
        let chain_id = self.runtime.application_creator_chain_id();
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
        token_0_creator_chain_id: ChainId,
        token_0: ApplicationId,
        amount_0: Amount,
        amount_1: Amount,
        virtual_liquidity: bool,
        to: Option<Account>,
    ) -> Result<SwapResponse, SwapError> {
        let caller_id = self.runtime.authenticated_caller_id().unwrap();
        let chain_id = self.runtime.chain_id();

        assert!(token_0 == caller_id, "Invalid caller");
        assert!(chain_id == token_0_creator_chain_id, "Invalid caller");

        let virtual_liquidity = self.formalize_virtual_liquidity(
            token_0_creator_chain_id,
            token_0,
            None,
            virtual_liquidity,
        );

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
                token_0_creator_chain_id,
                token_0,
                amount_0,
                amount_1,
                virtual_liquidity,
                to,
            })
            .with_authentication()
            .send_to(self.runtime.application_creator_chain_id());

        Ok(SwapResponse::Ok)
    }

    // Create pool with initial liquidity
    // If pool exists, do nothing
    // If not, create pool then let caller chain add liquidity
    async fn on_op_create_pool(
        &mut self,
        token_0: ApplicationId,
        token_1: ApplicationId,
        amount_0: Amount,
        amount_1: Amount,
        to: Option<Account>,
    ) -> Result<SwapResponse, SwapError> {
        self.runtime
            .prepare_message(SwapMessage::CreateUserPool {
                token_0,
                token_1,
                amount_0,
                amount_1,
                to,
            })
            .with_authentication()
            .send_to(self.runtime.application_creator_chain_id());
        Ok(SwapResponse::Ok)
    }

    // Pool application is run on its own chain
    async fn create_pool(
        &mut self,
        creator: Account,
        token_0_creator_chain_id: ChainId,
        token_0: ApplicationId,
        token_1_creator_chain_id: Option<ChainId>,
        token_1: Option<ApplicationId>,
        amount_0: Amount,
        amount_1: Amount,
        virtual_liquidity: bool,
        to: Option<Account>,
        deadline: Option<Timestamp>,
    ) -> Result<(), SwapError> {
        // For initial pool, all assets should be already authenticated when we're here
        // For user pool, we just create a pool, then notify user to add liquidity
        // 1: Create pool chain
        let (message_id, chain_id) = self.create_child_chain(token_0, token_1)?;

        self.state.create_pool_chain(chain_id, message_id)?;
        self.state
            .create_token_creator_chain_id(token_0, token_0_creator_chain_id)?;

        // 2: Create pool application with initial liquidity
        let bytecode_id = self.state.pool_bytecode_id().await;

        self.runtime
            .prepare_message(SwapMessage::CreatePool {
                creator,
                pool_bytecode_id: bytecode_id,
                token_0_creator_chain_id,
                token_0,
                token_1_creator_chain_id,
                token_1,
                amount_0,
                amount_1,
                virtual_initial_liquidity: virtual_liquidity,
                to,
            })
            .with_authentication()
            .send_to(chain_id);

        // Assets will be transfer to pool chain when create pool application
        Ok(())
    }

    async fn on_msg_initialize_liquidity(
        &mut self,
        token_0_creator_chain_id: ChainId,
        token_0: ApplicationId,
        amount_0: Amount,
        amount_1: Amount,
        virtual_liquidity: bool,
        to: Option<Account>,
    ) -> Result<(), SwapError> {
        let creator = self.message_owner_account();
        self.create_pool(
            creator,
            token_0_creator_chain_id,
            token_0,
            None,
            None,
            amount_0,
            amount_1,
            virtual_liquidity,
            to,
            None,
        )
        .await
    }

    fn on_msg_create_pool(
        &mut self,
        creator: Account,
        pool_bytecode_id: ModuleId,
        token_0_creator_chain_id: ChainId,
        token_0: ApplicationId,
        token_1_creator_chain_id: Option<ChainId>,
        token_1: Option<ApplicationId>,
        amount_0: Amount,
        amount_1: Amount,
        virtual_initial_liquidity: bool,
        to: Option<Account>,
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
                    virtual_initial_liquidity,
                    token_0_creator_chain_id,
                    token_1_creator_chain_id,
                },
                &PoolInstantiationArgument {
                    amount_0,
                    amount_1,
                    pool_fee_percent_mul_100: 30,
                    protocol_fee_percent_mul_100: 5,
                    router_application_id: application_id,
                },
                vec![],
            )
            .forget_abi();

        // Here we're on meme chain, we should goto swap chain to transfer funds due to we deposit
        // there
        let pool_application = Account {
            chain_id,
            owner: Some(AccountOwner::Application(pool_application_id)),
        };
        let creator_chain = self.runtime.application_creator_chain_id();
        self.runtime
            .prepare_message(SwapMessage::PoolCreated {
                creator,
                pool_application,
                token_0,
                token_1,
                amount_0,
                amount_1,
                virtual_initial_liquidity,
                to,
            })
            .with_authentication()
            .send_to(creator_chain);

        Ok(())
    }

    fn initial_pool_created(
        &mut self,
        pool_application: Account,
        token_0: ApplicationId,
        amount_0: Amount,
        amount_1: Amount,
        virtual_initial_liquidity: bool,
    ) {
        if !virtual_initial_liquidity {
            // This message may be authenticated by other user who is not the owner of swap
            // creation chain
            let application = AccountOwner::Application(self.runtime.application_id().forget_abi());
            self.runtime
                .transfer(Some(application), pool_application, amount_1);
        }

        // TODO: only call from InitializeLiquidity could transfer from application
        let call = MemeOperation::InitializeLiquidity {
            to: pool_application,
            amount: amount_0,
        };
        let _ = self
            .runtime
            .call_application(true, token_0.with_abi::<MemeAbi>(), &call);
    }

    fn user_pool_created(
        &mut self,
        creator: Account,
        pool_application: Account,
        token_0: ApplicationId,
        token_1: ApplicationId,
        amount_0: Amount,
        amount_1: Amount,
        to: Option<Account>,
    ) {
        self.runtime
            .prepare_message(SwapMessage::UserPoolCreated {
                pool_application,
                token_0,
                token_1,
                amount_0,
                amount_1,
                to,
            })
            .with_authentication()
            .send_to(creator.chain_id);
    }

    async fn on_msg_pool_created(
        &mut self,
        creator: Account,
        pool_application: Account,
        token_0: ApplicationId,
        token_1: Option<ApplicationId>,
        amount_0: Amount,
        amount_1: Amount,
        virtual_initial_liquidity: bool,
        to: Option<Account>,
    ) -> Result<(), SwapError> {
        assert!(amount_1 > Amount::ZERO, "Invalid amount");
        assert!(amount_0 > Amount::ZERO, "Invalid amount");

        if let Some(token_1) = token_1 {
            self.user_pool_created(
                creator,
                pool_application,
                token_0,
                token_1,
                amount_0,
                amount_1,
                to,
            );
        } else {
            self.initial_pool_created(
                pool_application,
                token_0,
                amount_0,
                amount_1,
                virtual_initial_liquidity,
            );
        }

        self.state
            .create_pool(token_0, token_1, pool_application)
            .await
    }

    async fn on_msg_user_pool_created(
        &mut self,
        pool_application: Account,
        _token_0: ApplicationId,
        _token_1: ApplicationId,
        amount_0: Amount,
        amount_1: Amount,
        to: Option<Account>,
    ) -> Result<(), SwapError> {
        // Now we're on our caller chain, we can call all liquidity like what we do in out wallet
        let call = PoolOperation::AddLiquidity {
            amount_0_in: amount_0,
            amount_1_in: amount_1,
            amount_0_out_min: None,
            amount_1_out_min: None,
            to,
            block_timestamp: None,
        };
        let Some(AccountOwner::Application(application_id)) = pool_application.owner else {
            panic!("Invalid application");
        };
        let _ = self
            .runtime
            .call_application(true, application_id.with_abi::<PoolAbi>(), &call);
        Ok(())
    }

    async fn on_msg_create_user_pool(
        &mut self,
        token_0: ApplicationId,
        token_1: ApplicationId,
        amount_0: Amount,
        amount_1: Amount,
        to: Option<Account>,
    ) -> Result<(), SwapError> {
        if let Some(_) = self
            .state
            .get_pool_exchangable(token_0, Some(token_1))
            .await?
        {
            panic!("Pool exists");
        }

        let token_0_creator_chain_id = self.state.token_creator_chain_id(token_0).await?;
        let token_1_creator_chain_id = self.state.token_creator_chain_id(token_1).await?;
        let creator = self.message_owner_account();

        self.create_pool(
            creator,
            token_0_creator_chain_id,
            token_0,
            Some(token_1_creator_chain_id),
            Some(token_1),
            amount_0,
            amount_1,
            false,
            to,
            None,
        )
        .await
    }
}

#[cfg(test)]
mod tests {
    use abi::{
        meme::MemeResponse,
        swap::router::{
            InstantiationArgument, SwapAbi, SwapOperation, SwapParameters, SwapResponse,
        },
    };
    use futures::FutureExt as _;
    use linera_sdk::{
        bcs,
        linera_base_types::{
            AccountOwner, Amount, ApplicationId, ApplicationPermissions, ChainId, ChainOwnership,
            MessageId, ModuleId, Owner,
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

        let meme_1_id = "78e404e4d0a94ee44a8bfb617cd4e6c3b3f3bc463a6dc46bec0914f85be37142b94e486abcfc016e937dad4297523060095f405530c95d498d981a94141589f167693295a14c3b48460ad6f75d67d2414428227550eb8cee8ecaa37e8646518300";
        let meme_1 = ApplicationId::from_str(meme_1_id).unwrap();

        let response = swap
            .execute_operation(SwapOperation::InitializeLiquidity {
                token_0_creator_chain_id: ChainId::from_str(
                    "aee928d4bf3880353b4a3cd9b6f88e6cc6e5ed050860abae439e7782e9b2dfe8",
                )
                .unwrap(),
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
    async fn operation_create_pool() {
        let mut swap = create_and_instantiate_swap();

        let meme_1_id = "78e404e4d0a94ee44a8bfb617cd4e6c3b3f3bc463a6dc46bec0914f85be37142b94e486abcfc016e937dad4297523060095f405530c95d498d981a94141589f167693295a14c3b48460ad6f75d67d2414428227550eb8cee8ecaa37e8646518300";
        let meme_1 = ApplicationId::from_str(meme_1_id).unwrap();

        let meme_2_id = "78e404e4d0a94ee44a8bfb617cd4e6c3b3f3bc463a6dc46bec0914f85be37142b94e486abcfc016e937dad4297523060095f405530c95d498d981a94141589f167693295a14c3b48460ad6f75d67d2414428227550eb8cee8ecaa37e8646518301";
        let meme_2 = ApplicationId::from_str(meme_1_id).unwrap();

        let response = swap
            .execute_operation(SwapOperation::CreatePool {
                token_0: meme_1,
                token_1: meme_2,
                amount_0: Amount::ONE,
                amount_1: Amount::ONE,
                to: None,
            })
            .await;

        assert!(matches!(response, SwapResponse::Ok));
    }

    #[test]
    fn message() {}

    #[test]
    fn cross_application_call() {}

    fn mock_application_call(
        _authenticated: bool,
        _application_id: ApplicationId,
        _operation: Vec<u8>,
    ) -> Vec<u8> {
        bcs::to_bytes(&MemeResponse::ChainId(
            ChainId::from_str("aee928d4bf3880353b4a3cd9b6f88e6cc6e5ed050860abae439e7782e9b2dfe8")
                .unwrap(),
        ))
        .unwrap()
    }

    fn create_and_instantiate_swap() -> SwapContract {
        let owner =
            Owner::from_str("02e900512d2fca22897f80a2f6932ff454f2752ef7afad18729dd25e5b5b6e00")
                .unwrap();
        let application_id_str = "78e404e4d0a94ee44a8bfb617cd4e6c3b3f3bc463a6dc46bec0914f85be37142b94e486abcfc016e937dad4297523060095f405530c95d498d981a94141589f167693295a14c3b48460ad6f75d67d2414428227550eb8cee8ecaa37e8646518301";
        let application_id = ApplicationId::from_str(application_id_str)
            .unwrap()
            .with_abi::<SwapAbi>();
        let message_id = MessageId::from_str("dad01517c7a3c428ea903253a9e59964e8db06d323a9bd3f4c74d6366832bdbf801200000000000000000000").unwrap();
        let meme_1_id = "78e404e4d0a94ee44a8bfb617cd4e6c3b3f3bc463a6dc46bec0914f85be37142b94e486abcfc016e937dad4297523060095f405530c95d498d981a94141589f167693295a14c3b48460ad6f75d67d2414428227550eb8cee8ecaa37e8646518300";
        let meme_1 = ApplicationId::from_str(meme_1_id).unwrap();
        let meme_1_chain_id =
            ChainId::from_str("aee928d4bf3880353b4a3cd9b6f88e6cc6e5ed050860abae439e7782e9b2dfe8")
                .unwrap();
        let chain_id =
            ChainId::from_str("aee928d4bf3880353b4a3cd9b6f88e6cc6e5ed050860abae439e7782e9b2dfe9")
                .unwrap();

        let mut runtime = ContractRuntime::new()
            .with_application_parameters(SwapParameters {})
            .with_application_id(application_id)
            .with_authenticated_signer(owner)
            .with_authenticated_caller_id(meme_1)
            .with_chain_id(meme_1_chain_id)
            .with_application_creator_chain_id(chain_id)
            .with_call_application_handler(mock_application_call)
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
                pool_bytecode_id: bytecode_id,
            })
            .now_or_never()
            .expect("Initialization of swap state should not await anything");

        contract
    }
}
