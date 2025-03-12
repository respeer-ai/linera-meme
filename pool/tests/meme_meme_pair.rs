// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

//! Integration tests for the Pool application.

#![cfg(not(target_arch = "wasm32"))]

use abi::{
    constant::OPEN_CHAIN_FEE_BUDGET,
    meme::{
        InstantiationArgument as MemeInstantiationArgument, Liquidity, Meme, MemeAbi,
        MemeParameters, Metadata,
    },
    store_type::StoreType,
    swap::{
        pool::{
            InstantiationArgument as PoolInstantiationArgument, Pool, PoolAbi, PoolOperation,
            PoolParameters,
        },
        router::{
            InstantiationArgument as SwapInstantiationArgument, Pool as PoolIndex, SwapAbi,
            SwapParameters,
        },
    },
};
use linera_sdk::{
    linera_base_types::{
        Account, AccountOwner, Amount, ApplicationId, ChainDescription, ChainId, MessageId,
        ModuleId, Owner,
    },
    test::{ActiveChain, Medium, MessageAction, QueryOutcome, Recipient, TestValidator},
};
use std::str::FromStr;

#[derive(Clone)]
struct TestSuite {
    validator: TestValidator,

    admin_chain: ActiveChain,
    meme_chain_1: ActiveChain,
    meme_chain_2: ActiveChain,
    user_chain: ActiveChain,
    pool_chain: Option<ActiveChain>,
    swap_chain: ActiveChain,

    pool_bytecode_id: ModuleId<PoolAbi, PoolParameters, PoolInstantiationArgument>,
    pool_application_id: Option<ApplicationId<PoolAbi>>,
    meme_application_id_1: Option<ApplicationId<MemeAbi>>,
    meme_application_id_2: Option<ApplicationId<MemeAbi>>,
    swap_application_id: Option<ApplicationId<SwapAbi>>,

    initial_supply: Amount,
    initial_liquidity: Amount,
    initial_native: Amount,
}

impl TestSuite {
    async fn new() -> Self {
        let (validator, pool_bytecode_id) = TestValidator::with_current_module::<
            PoolAbi,
            PoolParameters,
            PoolInstantiationArgument,
        >()
        .await;

        let admin_chain = validator.get_chain(&ChainId::root(0));
        let meme_chain_1 = validator.new_chain().await;
        let meme_chain_2 = validator.new_chain().await;
        let user_chain = validator.new_chain().await;
        let swap_chain = validator.new_chain().await;

        TestSuite {
            validator,

            admin_chain,
            meme_chain_1,
            meme_chain_2,
            user_chain,
            pool_chain: None,
            swap_chain,

            pool_bytecode_id,
            pool_application_id: None,
            meme_application_id_1: None,
            meme_application_id_2: None,
            swap_application_id: None,

            initial_supply: Amount::from_tokens(21000000),
            initial_liquidity: Amount::from_tokens(11000000),
            initial_native: Amount::from_tokens(10),
        }
    }

    fn chain_account(&self, chain: ActiveChain) -> Account {
        Account {
            chain_id: chain.id(),
            owner: None,
        }
    }

    fn chain_owner_account(&self, chain: &ActiveChain) -> Account {
        Account {
            chain_id: chain.id(),
            owner: Some(AccountOwner::User(Owner::from(chain.public_key()))),
        }
    }

    fn application_account(&self, chain_id: ChainId, application_id: ApplicationId) -> Account {
        Account {
            chain_id,
            owner: Some(AccountOwner::Application(application_id.forget_abi())),
        }
    }

    async fn fund_chain(&self, chain: &ActiveChain, amount: Amount) {
        let certificate = self
            .admin_chain
            .add_block(|block| {
                block.with_native_token_transfer(
                    None,
                    Recipient::Account(self.chain_account(chain.clone())),
                    amount,
                );
            })
            .await;
        chain
            .add_block(move |block| {
                block.with_messages_from_by_medium(
                    &certificate,
                    &Medium::Direct,
                    MessageAction::Accept,
                );
            })
            .await;
        chain.handle_received_messages().await;
    }

    async fn create_swap_application(&mut self) {
        let swap_bytecode_id = self.swap_chain.publish_bytecode_files_in("../swap").await;

        self.swap_application_id = Some(
            self.swap_chain
                .create_application::<SwapAbi, SwapParameters, SwapInstantiationArgument>(
                    swap_bytecode_id,
                    SwapParameters {},
                    SwapInstantiationArgument {
                        pool_bytecode_id: self.pool_bytecode_id.forget_abi(),
                    },
                    vec![],
                )
                .await,
        )
    }

    async fn create_meme_applications(&mut self, virtual_initial_liquidity: bool) {
        let instantiation_argument = MemeInstantiationArgument {
            meme: Meme {
                name: "Test Token".to_string(),
                ticker: "LTT".to_string(),
                decimals: 6,
                initial_supply: self.initial_supply,
                total_supply: self.initial_supply,
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
            blob_gateway_application_id: None,
            ams_application_id: None,
            proxy_application_id: None,
            swap_application_id: Some(self.swap_application_id.unwrap().forget_abi()),
        };
        let parameters = MemeParameters {
            creator: self.chain_owner_account(&self.meme_chain_1),
            initial_liquidity: Some(Liquidity {
                fungible_amount: self.initial_liquidity,
                native_amount: self.initial_native,
            }),
            virtual_initial_liquidity,
            swap_creator_chain_id: self.swap_chain.id(),
        };

        let meme_bytecode_id = self.meme_chain_1.publish_bytecode_files_in("../meme").await;
        self.meme_application_id_1 = Some(
            self.meme_chain_1
                .create_application(
                    meme_bytecode_id,
                    parameters.clone(),
                    instantiation_argument.clone(),
                    vec![],
                )
                .await,
        );

        let parameters = MemeParameters {
            creator: self.chain_owner_account(&self.meme_chain_2),
            initial_liquidity: Some(Liquidity {
                fungible_amount: self.initial_liquidity,
                native_amount: self.initial_native,
            }),
            virtual_initial_liquidity,
            swap_creator_chain_id: self.swap_chain.id(),
        };
        self.meme_application_id_2 = Some(
            self.meme_chain_2
                .create_application(
                    meme_bytecode_id,
                    parameters.clone(),
                    instantiation_argument.clone(),
                    vec![],
                )
                .await,
        );
    }

    async fn swap(&self, chain: &ActiveChain, amount: Amount) {
        chain
            .add_block(|block| {
                block.with_operation(
                    self.pool_application_id.unwrap(),
                    PoolOperation::Swap {
                        amount_0_in: None,
                        amount_1_in: Some(amount),
                        amount_0_out_min: None,
                        amount_1_out_min: None,
                        to: None,
                        block_timestamp: None,
                    },
                );
            })
            .await;
        self.meme_chain_1.handle_received_messages().await;
        self.meme_chain_2.handle_received_messages().await;
        chain.handle_received_messages().await;
        self.pool_chain
            .clone()
            .unwrap()
            .handle_received_messages()
            .await;
        self.pool_chain
            .clone()
            .unwrap()
            .handle_received_messages()
            .await;
        self.meme_chain_1.handle_received_messages().await;
        self.meme_chain_2.handle_received_messages().await;
        chain.handle_received_messages().await;
    }

    async fn add_liquidity(&self, chain: &ActiveChain, amount_0: Amount, amount_1: Amount) {
        chain
            .add_block(|block| {
                block.with_operation(
                    self.pool_application_id.unwrap(),
                    PoolOperation::AddLiquidity {
                        amount_0_in: amount_0,
                        amount_1_in: amount_1,
                        amount_0_out_min: None,
                        amount_1_out_min: None,
                        to: None,
                        block_timestamp: None,
                    },
                );
            })
            .await;
        self.meme_chain_1.handle_received_messages().await;
        self.meme_chain_2.handle_received_messages().await;
        chain.handle_received_messages().await;
        chain.handle_received_messages().await;
        chain.handle_received_messages().await;
        self.pool_chain
            .clone()
            .unwrap()
            .handle_received_messages()
            .await;
        self.pool_chain
            .clone()
            .unwrap()
            .handle_received_messages()
            .await;
        chain.handle_received_messages().await;
    }
}

/// Test setting a pool and testing its coherency across microchains.
///
/// Creates the application on a `chain`, initializing it with a 42 then adds 15 and obtains 57.
/// which is then checked.
#[tokio::test(flavor = "multi_thread")]
async fn meme_meme_pair_test() {
    let _ = env_logger::builder().is_test(true).try_init();

    let mut suite = TestSuite::new().await;
    let meme_chain_1 = &suite.meme_chain_1.clone();
    let meme_chain_2 = &suite.meme_chain_2.clone();
    let user_chain = &suite.user_chain.clone();
    let swap_chain = &suite.swap_chain.clone();

    let swap_key_pair = swap_chain.key_pair();

    suite.fund_chain(&meme_chain_1, OPEN_CHAIN_FEE_BUDGET).await;
    suite.fund_chain(&meme_chain_2, OPEN_CHAIN_FEE_BUDGET).await;

    suite.create_swap_application().await;
    suite.create_meme_applications(true).await;

    // Check initial swap pool
    meme_chain_1.handle_received_messages().await;
    meme_chain_2.handle_received_messages().await;
    swap_chain.handle_received_messages().await;
}
