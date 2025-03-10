// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

//! Integration tests for the Pool application.

#![cfg(not(target_arch = "wasm32"))]

use abi::{
    meme::{
        InstantiationArgument as MemeInstantiationArgument, Liquidity, Meme, MemeAbi,
        MemeParameters, Metadata,
    },
    store_type::StoreType,
    swap::{
        pool::{InstantiationArgument as PoolInstantiationArgument, PoolAbi, PoolParameters},
        router::{InstantiationArgument as SwapInstantiationArgument, SwapAbi, SwapParameters},
    },
};
use linera_sdk::{
    linera_base_types::{Account, AccountOwner, Amount, ApplicationId, ChainId, ModuleId, Owner},
    test::{ActiveChain, QueryOutcome, TestValidator},
};

struct TestSuite {
    admin_chain: ActiveChain,
    meme_chain: ActiveChain,
    user_chain: ActiveChain,
    pool_chain: ActiveChain,
    swap_chain: ActiveChain,

    pool_bytecode_id: ModuleId<PoolAbi, PoolParameters, PoolInstantiationArgument>,
    pool_application_id: Option<ApplicationId<PoolAbi>>,
    meme_application_id: Option<ApplicationId<MemeAbi>>,
    swap_application_id: Option<ApplicationId<SwapAbi>>,

    initial_supply: Amount,
    initial_liquidity: Amount,
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
        let meme_chain = validator.new_chain().await;
        let user_chain = validator.new_chain().await;
        let pool_chain = validator.new_chain().await;
        let swap_chain = validator.new_chain().await;

        TestSuite {
            admin_chain,
            meme_chain,
            user_chain,
            pool_chain,
            swap_chain,

            pool_bytecode_id,
            pool_application_id: None,
            meme_application_id: None,
            swap_application_id: None,

            initial_supply: Amount::from_tokens(21000000),
            initial_liquidity: Amount::from_tokens(11000000),
        }
    }

    fn chain_owner_account(&self, chain: &ActiveChain) -> Account {
        Account {
            chain_id: chain.id(),
            owner: Some(AccountOwner::User(Owner::from(chain.public_key()))),
        }
    }

    async fn create_swap_application(&mut self) {
        let swap_bytecode_id = self.swap_chain.publish_bytecode_files_in("../swap").await;

        self.swap_application_id = Some(
            self.swap_chain
                .create_application::<SwapAbi, (), SwapInstantiationArgument>(
                    swap_bytecode_id,
                    (),
                    SwapInstantiationArgument {
                        pool_bytecode_id: self.pool_bytecode_id.forget_abi(),
                    },
                    vec![],
                )
                .await,
        )
    }

    async fn create_meme_application(&mut self) {
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
            creator: self.chain_owner_account(&self.meme_chain),
            initial_liquidity: Some(Liquidity {
                fungible_amount: self.initial_liquidity,
                native_amount: Amount::from_tokens(10),
            }),
            virtual_initial_liquidity: true,
        };

        let meme_bytecode_id = self.swap_chain.publish_bytecode_files_in("../meme").await;
        self.meme_application_id = Some(
            self.meme_chain
                .create_application(
                    meme_bytecode_id,
                    parameters.clone(),
                    instantiation_argument.clone(),
                    vec![],
                )
                .await,
        )
    }

    async fn create_pool_application(&mut self) {
        self.pool_application_id = Some(
            self.pool_chain
                .create_application::<PoolAbi, PoolParameters, PoolInstantiationArgument>(
                    self.pool_bytecode_id,
                    PoolParameters {
                        token_0: self.meme_application_id.unwrap().forget_abi(),
                        token_1: None,
                        virtual_initial_liquidity: true,
                    },
                    PoolInstantiationArgument {
                        amount_0: Amount::from_tokens(10000),
                        amount_1: Amount::from_tokens(10),
                        pool_fee_percent_mul_100: 30,
                        protocol_fee_percent_mul_100: 5,
                        router_application_id: self.swap_application_id.unwrap().forget_abi(),
                    },
                    vec![],
                )
                .await,
        )
    }
}

/// Test setting a pool and testing its coherency across microchains.
///
/// Creates the application on a `chain`, initializing it with a 42 then adds 15 and obtains 57.
/// which is then checked.
#[tokio::test(flavor = "multi_thread")]
async fn pool_test() {
    let _ = env_logger::builder().is_test(true).try_init();

    let mut suite = TestSuite::new().await;
    let meme_chain = &suite.meme_chain.clone();
    let user_chain = &suite.user_chain.clone();
    let pool_chain = &suite.pool_chain.clone();

    suite.create_swap_application().await;
    suite.create_meme_application().await;
    suite.create_pool_application().await;
}
