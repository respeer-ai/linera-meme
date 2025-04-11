// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

//! Integration tests for the Swap application.

#![cfg(not(target_arch = "wasm32"))]

use abi::{
    meme::{
        InstantiationArgument as MemeInstantiationArgument, Liquidity, Meme, MemeAbi,
        MemeParameters, Metadata,
    },
    policy::open_chain_fee_budget,
    store_type::StoreType,
    swap::router::{
        InstantiationArgument as SwapInstantiationArgument, Pool, SwapAbi, SwapParameters,
    },
};
use linera_sdk::{
    linera_base_types::{
        Account, AccountOwner, Amount, ApplicationId, ChainDescription, ChainId, CryptoHash,
        MessageId, ModuleId, TestString,
    },
    test::{ActiveChain, Medium, MessageAction, QueryOutcome, Recipient, TestValidator},
};
use std::str::FromStr;

#[derive(Clone)]
struct TestSuite {
    pub validator: TestValidator,

    pub admin_chain: ActiveChain,
    pub meme_chain: ActiveChain,
    pub swap_chain: ActiveChain,

    pub swap_application_id: Option<ApplicationId<SwapAbi>>,
    pub meme_application_id: Option<ApplicationId<MemeAbi>>,

    pub swap_bytecode_id: ModuleId<SwapAbi, SwapParameters, SwapInstantiationArgument>,
    pub meme_bytecode_id: ModuleId<MemeAbi, MemeParameters, MemeInstantiationArgument>,

    pub initial_supply: Amount,
    pub initial_liquidity: Amount,
    pub initial_native: Amount,
}

impl TestSuite {
    async fn new() -> Self {
        let (validator, swap_bytecode_id) = TestValidator::with_current_module::<
            SwapAbi,
            SwapParameters,
            SwapInstantiationArgument,
        >()
        .await;

        let admin_chain = validator.get_chain(&ChainId::root(0));
        let meme_chain = validator.new_chain().await;
        let swap_chain = validator.new_chain().await;

        let meme_bytecode_id = swap_chain.publish_bytecode_files_in("../meme").await;

        TestSuite {
            validator,

            admin_chain,
            meme_chain,
            swap_chain,

            swap_application_id: None,
            meme_application_id: None,

            swap_bytecode_id,
            meme_bytecode_id,

            initial_supply: Amount::from_tokens(21000000),
            initial_liquidity: Amount::from_tokens(11000000),
            initial_native: Amount::from_tokens(10),
        }
    }

    fn chain_account(&self, chain: ActiveChain) -> Account {
        Account {
            chain_id: chain.id(),
            owner: AccountOwner::CHAIN,
        }
    }

    fn chain_owner_account(&self, chain: &ActiveChain) -> Account {
        Account {
            chain_id: chain.id(),
            owner: AccountOwner::from(chain.public_key()),
        }
    }

    fn application_account(&self, chain_id: ChainId, application_id: ApplicationId) -> Account {
        Account {
            chain_id,
            owner: AccountOwner::from(application_id.forget_abi()),
        }
    }

    async fn fund_chain(&self, chain: &ActiveChain, amount: Amount) {
        let certificate = self
            .admin_chain
            .add_block(|block| {
                block.with_native_token_transfer(
                    AccountOwner::CHAIN,
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
        let pool_bytecode_id = self.swap_chain.publish_bytecode_files_in("../pool").await;

        self.swap_application_id = Some(
            self.swap_chain
                .create_application::<SwapAbi, SwapParameters, SwapInstantiationArgument>(
                    self.swap_bytecode_id,
                    SwapParameters {},
                    SwapInstantiationArgument { pool_bytecode_id },
                    vec![],
                )
                .await,
        )
    }

    async fn create_meme_application(&mut self, virtual_initial_liquidity: bool) {
        let instantiation_argument = MemeInstantiationArgument {
            meme: Meme {
                name: "Test Token".to_string(),
                ticker: "LTT".to_string(),
                decimals: 6,
                initial_supply: self.initial_supply,
                total_supply: self.initial_supply,
                metadata: Metadata {
                    logo_store_type: StoreType::S3,
                    logo: Some(CryptoHash::new(&TestString::new("Test Logo".to_string()))),
                    description: "Test token description".to_string(),
                    twitter: None,
                    telegram: None,
                    discord: None,
                    website: None,
                    github: None,
                    live_stream: None,
                },
                virtual_initial_liquidity,
                initial_liquidity: None,
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
                native_amount: self.initial_native,
            }),
            virtual_initial_liquidity,
            swap_creator_chain_id: self.swap_chain.id(),
        };

        self.meme_application_id = Some(
            self.meme_chain
                .create_application(
                    self.meme_bytecode_id,
                    parameters.clone(),
                    instantiation_argument.clone(),
                    vec![],
                )
                .await,
        )
    }
}

/// Test setting a swap and testing its coherency across microchains.
#[tokio::test(flavor = "multi_thread")]
async fn virtual_liquidity_native_test() {
    let _ = env_logger::builder().is_test(true).try_init();

    let _ = env_logger::builder().is_test(true).try_init();

    let mut suite = TestSuite::new().await;
    let meme_chain = suite.meme_chain.clone();
    let swap_chain = suite.swap_chain.clone();

    let swap_key_pair = swap_chain.key_pair();

    suite.fund_chain(&meme_chain, open_chain_fee_budget()).await;
    assert_eq!(meme_chain.chain_balance().await, open_chain_fee_budget());

    suite.create_swap_application().await;
    suite.create_meme_application(true).await;

    meme_chain.handle_received_messages().await;
    swap_chain.handle_received_messages().await;

    let query = format!(
        "query {{ allowanceOf(owner: \"{}\", spender: \"{}\") }}",
        suite.application_account(
            meme_chain.id(),
            suite.meme_application_id.unwrap().forget_abi()
        ),
        suite.application_account(
            swap_chain.id(),
            suite.swap_application_id.unwrap().forget_abi()
        ),
    );
    let QueryOutcome { response, .. } = meme_chain
        .graphql_query(suite.meme_application_id.unwrap(), query)
        .await;
    assert_eq!(
        Amount::from_str(response["allowanceOf"].as_str().unwrap()).unwrap(),
        suite.initial_liquidity,
    );

    let QueryOutcome { response, .. } = swap_chain
        .graphql_query(
            suite.swap_application_id.unwrap(),
            "query { poolChainCreationMessages }",
        )
        .await;
    assert_eq!(
        response["poolChainCreationMessages"]
            .as_array()
            .unwrap()
            .len(),
        1,
    );

    let message_id = MessageId::from_str(
        response["poolChainCreationMessages"].as_array().unwrap()[0]
            .as_str()
            .unwrap(),
    )
    .unwrap();
    let description = ChainDescription::Child(message_id);
    let pool_chain = ActiveChain::new(swap_key_pair.copy(), description, suite.clone().validator);
    suite.validator.add_chain(pool_chain.clone());

    pool_chain.handle_received_messages().await;
    swap_chain.handle_received_messages().await;
    meme_chain.handle_received_messages().await;

    // Now the open chain funds should be transferred to pool
    assert_eq!(meme_chain.chain_balance().await, Amount::ZERO);
    assert_eq!(swap_chain.chain_balance().await, Amount::ZERO);
    assert_eq!(pool_chain.chain_balance().await, open_chain_fee_budget());

    let QueryOutcome { response, .. } = swap_chain
        .graphql_query(
            suite.swap_application_id.unwrap(),
            "query { pools {
                creator
                poolId
                token0
                token1
                poolApplication
                createdAt
            }}",
        )
        .await;
    assert_eq!(response["pools"].as_array().unwrap().len(), 1,);

    let pool: Pool =
        serde_json::from_value(response["pools"].as_array().unwrap()[0].clone()).unwrap();

    let query = format!(
        "query {{ allowanceOf(owner: \"{}\", spender: \"{}\") }}",
        suite.application_account(
            meme_chain.id(),
            suite.meme_application_id.unwrap().forget_abi()
        ),
        suite.application_account(
            swap_chain.id(),
            suite.swap_application_id.unwrap().forget_abi()
        ),
    );
    let QueryOutcome { response, .. } = meme_chain
        .graphql_query(suite.meme_application_id.unwrap(), query)
        .await;
    assert_eq!(
        Amount::from_str(response["allowanceOf"].as_str().unwrap()).unwrap(),
        Amount::ZERO,
    );

    let query = format!("query {{ balanceOf(owner: \"{}\")}}", pool.pool_application,);
    let QueryOutcome { response, .. } = meme_chain
        .graphql_query(suite.meme_application_id.unwrap(), query)
        .await;
    assert_eq!(
        Amount::from_str(response["balanceOf"].as_str().unwrap()).unwrap(),
        suite.initial_liquidity,
    );
}

#[tokio::test(flavor = "multi_thread")]
async fn real_liquidity_native_test() {
    let _ = env_logger::builder().is_test(true).try_init();

    let _ = env_logger::builder().is_test(true).try_init();

    let mut suite = TestSuite::new().await;
    let meme_chain = suite.meme_chain.clone();
    let swap_chain = suite.swap_chain.clone();

    let swap_key_pair = swap_chain.key_pair();

    let amount = suite
        .initial_native
        .try_add(open_chain_fee_budget())
        .unwrap();
    suite.fund_chain(&meme_chain, amount).await;
    assert_eq!(meme_chain.chain_balance().await, amount);

    suite.create_swap_application().await;
    suite.create_meme_application(false).await;

    meme_chain.handle_received_messages().await;
    swap_chain.handle_received_messages().await;

    let query = format!(
        "query {{ allowanceOf(owner: \"{}\", spender: \"{}\") }}",
        suite.application_account(
            meme_chain.id(),
            suite.meme_application_id.unwrap().forget_abi()
        ),
        suite.application_account(
            swap_chain.id(),
            suite.swap_application_id.unwrap().forget_abi()
        ),
    );
    let QueryOutcome { response, .. } = meme_chain
        .graphql_query(suite.meme_application_id.unwrap(), query)
        .await;
    assert_eq!(
        Amount::from_str(response["allowanceOf"].as_str().unwrap()).unwrap(),
        suite.initial_liquidity,
    );

    // Here liquidity funds should already be transferred to swap application on creation chain.
    // open_chain_fee_budget() is already transferred to pool chain here so on swap chain we have
    // initial native amount. Pool chain is not executed here so it should still be zero tokens.
    assert_eq!(
        swap_chain
            .owner_balance(
                &suite
                    .application_account(
                        swap_chain.id(),
                        suite.swap_application_id.unwrap().forget_abi()
                    )
                    .owner
            )
            .await,
        Some(suite.initial_native)
    );
    assert_eq!(meme_chain.chain_balance().await, Amount::ZERO);
    assert_eq!(swap_chain.chain_balance().await, Amount::ZERO);

    let QueryOutcome { response, .. } = swap_chain
        .graphql_query(
            suite.swap_application_id.unwrap(),
            "query { poolChainCreationMessages }",
        )
        .await;
    assert_eq!(
        response["poolChainCreationMessages"]
            .as_array()
            .unwrap()
            .len(),
        1,
    );

    let message_id = MessageId::from_str(
        response["poolChainCreationMessages"].as_array().unwrap()[0]
            .as_str()
            .unwrap(),
    )
    .unwrap();
    let description = ChainDescription::Child(message_id);
    let pool_chain = ActiveChain::new(swap_key_pair.copy(), description, suite.clone().validator);
    suite.validator.add_chain(pool_chain.clone());

    // Open chain fee is already funded
    assert_eq!(pool_chain.chain_balance().await, open_chain_fee_budget());

    pool_chain.handle_received_messages().await;
    swap_chain.handle_received_messages().await;
    meme_chain.handle_received_messages().await;

    // Now the open chain funds should be transferred to pool
    assert_eq!(meme_chain.chain_balance().await, Amount::ZERO);
    assert_eq!(swap_chain.chain_balance().await, Amount::ZERO);
    assert_eq!(pool_chain.chain_balance().await, open_chain_fee_budget());

    let QueryOutcome { response, .. } = swap_chain
        .graphql_query(
            suite.swap_application_id.unwrap(),
            "query { pools {
                creator
                poolId
                token0
                token1
                poolApplication
                createdAt
            }}",
        )
        .await;
    assert_eq!(response["pools"].as_array().unwrap().len(), 1,);

    let pool: Pool =
        serde_json::from_value(response["pools"].as_array().unwrap()[0].clone()).unwrap();

    // Here pool application is still be zero
    assert_eq!(
        pool_chain
            .owner_balance(&pool.pool_application.owner)
            .await
            .is_none(),
        true
    );

    pool_chain.handle_received_messages().await;
    assert_eq!(
        pool_chain.owner_balance(&pool.pool_application.owner).await,
        Some(suite.initial_native)
    );

    let query = format!(
        "query {{ allowanceOf(owner: \"{}\", spender: \"{}\") }}",
        suite.application_account(
            meme_chain.id(),
            suite.meme_application_id.unwrap().forget_abi()
        ),
        suite.application_account(
            swap_chain.id(),
            suite.swap_application_id.unwrap().forget_abi()
        ),
    );
    let QueryOutcome { response, .. } = meme_chain
        .graphql_query(suite.meme_application_id.unwrap(), query)
        .await;
    assert_eq!(
        Amount::from_str(response["allowanceOf"].as_str().unwrap()).unwrap(),
        Amount::ZERO,
    );

    let query = format!("query {{ balanceOf(owner: \"{}\")}}", pool.pool_application,);
    let QueryOutcome { response, .. } = meme_chain
        .graphql_query(suite.meme_application_id.unwrap(), query)
        .await;
    assert_eq!(
        Amount::from_str(response["balanceOf"].as_str().unwrap()).unwrap(),
        suite.initial_liquidity,
    );
}
