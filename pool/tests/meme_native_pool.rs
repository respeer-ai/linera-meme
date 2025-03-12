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
    meme_chain: ActiveChain,
    user_chain: ActiveChain,
    pool_chain: Option<ActiveChain>,
    swap_chain: ActiveChain,

    pool_bytecode_id: ModuleId<PoolAbi, PoolParameters, PoolInstantiationArgument>,
    pool_application_id: Option<ApplicationId<PoolAbi>>,
    meme_application_id: Option<ApplicationId<MemeAbi>>,
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
        let meme_chain = validator.new_chain().await;
        let user_chain = validator.new_chain().await;
        let swap_chain = validator.new_chain().await;

        TestSuite {
            validator,

            admin_chain,
            meme_chain,
            user_chain,
            pool_chain: None,
            swap_chain,

            pool_bytecode_id,
            pool_application_id: None,
            meme_application_id: None,
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
                native_amount: self.initial_native,
            }),
            virtual_initial_liquidity,
            swap_creator_chain_id: self.swap_chain.id(),
        };

        let meme_bytecode_id = self.meme_chain.publish_bytecode_files_in("../meme").await;
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
        self.meme_chain.handle_received_messages().await;
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
        self.meme_chain.handle_received_messages().await;
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
        self.meme_chain.handle_received_messages().await;
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
async fn pool_virtual_initial_liquidity_test() {
    let _ = env_logger::builder().is_test(true).try_init();

    let mut suite = TestSuite::new().await;
    let meme_chain = &suite.meme_chain.clone();
    let user_chain = &suite.user_chain.clone();
    let swap_chain = &suite.swap_chain.clone();

    let swap_key_pair = swap_chain.key_pair();

    suite.fund_chain(&meme_chain, OPEN_CHAIN_FEE_BUDGET).await;

    suite.create_swap_application().await;
    suite.create_meme_application(true).await;

    // Check initial swap pool
    meme_chain.handle_received_messages().await;
    swap_chain.handle_received_messages().await;

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
    suite.pool_chain = Some(pool_chain.clone());

    pool_chain.handle_received_messages().await;
    swap_chain.handle_received_messages().await;
    meme_chain.handle_received_messages().await;

    let QueryOutcome { response, .. } = swap_chain
        .graphql_query(
            suite.swap_application_id.unwrap(),
            "query { pools {
                poolId
                token0
                token1
                poolApplication
            } }",
        )
        .await;
    assert_eq!(response["pools"].as_array().unwrap().len(), 1,);
    let pool: PoolIndex =
        serde_json::from_value(response["pools"].as_array().unwrap()[0].clone()).unwrap();

    let Some(AccountOwner::Application(pool_application_id)) = pool.pool_application.owner else {
        panic!("Invalid pool application");
    };
    suite.pool_application_id = Some(pool_application_id.with_abi::<PoolAbi>());

    let QueryOutcome { response, .. } = pool_chain
        .graphql_query(suite.pool_application_id.unwrap(), "query { pool }")
        .await;
    let pool: Pool = serde_json::from_value(response["pool"].clone()).unwrap();

    assert_eq!(OPEN_CHAIN_FEE_BUDGET, pool_chain.chain_balance().await);
    assert_eq!(suite.initial_native, pool.reserve_1);
    assert_eq!(suite.initial_liquidity, pool.reserve_0);

    let pool_application_account = suite.application_account(
        pool_chain.id(),
        suite.pool_application_id.unwrap().forget_abi(),
    );
    let query = format!(
        "query {{ balanceOf(owner: \"{}\")}}",
        pool_application_account,
    );
    let QueryOutcome { response, .. } = meme_chain
        .graphql_query(suite.meme_application_id.unwrap(), query)
        .await;
    assert_eq!(
        Amount::from_str(response["balanceOf"].as_str().unwrap()).unwrap(),
        suite.initial_liquidity,
    );

    // Swap
    let balance = Amount::from_str("20.1").unwrap();
    let budget = Amount::from_str("9.8").unwrap();

    suite.fund_chain(&user_chain, balance).await;
    suite.swap(&user_chain, budget).await;

    assert_eq!(
        balance.try_sub(budget).unwrap(),
        user_chain.chain_balance().await
    );
    assert_eq!(OPEN_CHAIN_FEE_BUDGET, pool_chain.chain_balance().await);
    assert_eq!(
        budget,
        pool_chain
            .owner_balance(&AccountOwner::Application(pool_application_id))
            .await
            .unwrap()
    );

    let QueryOutcome { response, .. } = pool_chain
        .graphql_query(suite.pool_application_id.unwrap(), "query { pool }")
        .await;
    let pool: Pool = serde_json::from_value(response["pool"].clone()).unwrap();

    assert_eq!(OPEN_CHAIN_FEE_BUDGET, pool_chain.chain_balance().await);
    assert_eq!(Amount::from_attos(19800000000000000000), pool.reserve_1);
    assert_eq!(Amount::from_attos(220000000000000000000000), pool.reserve_0);

    let user_account = suite.chain_owner_account(&user_chain);
    let query = format!("query {{ balanceOf(owner: \"{}\")}}", user_account);
    let QueryOutcome { response, .. } = meme_chain
        .graphql_query(suite.meme_application_id.unwrap(), query)
        .await;
    assert_eq!(
        Amount::from_str(response["balanceOf"].as_str().unwrap()).unwrap(),
        Amount::from_attos(10780000000000000000000000),
    );

    let query = format!(
        "query {{ balanceOf(owner: \"{}\")}}",
        pool_application_account,
    );
    let QueryOutcome { response, .. } = meme_chain
        .graphql_query(suite.meme_application_id.unwrap(), query)
        .await;
    assert_eq!(
        Amount::from_str(response["balanceOf"].as_str().unwrap()).unwrap(),
        Amount::from_attos(220000000000000000000000),
    );

    // Add liquidity
    suite
        .add_liquidity(
            &user_chain,
            Amount::from_attos(1085715329991143570652),
            balance.try_sub(budget).unwrap(),
        )
        .await;
    let liquidity_fund_amount = Amount::from_attos(9897714379699202921);
    assert_eq!(
        liquidity_fund_amount,
        pool_chain
            .owner_balance(&AccountOwner::Application(pool_application_id))
            .await
            .unwrap()
    );
    assert_eq!(
        balance.try_sub(liquidity_fund_amount).unwrap(),
        user_chain
            .owner_balance(&user_account.owner.unwrap())
            .await
            .unwrap()
    );

    let QueryOutcome { response, .. } = pool_chain
        .graphql_query(suite.pool_application_id.unwrap(), "query { pool }")
        .await;
    let pool: Pool = serde_json::from_value(response["pool"].clone()).unwrap();

    assert_eq!(OPEN_CHAIN_FEE_BUDGET, pool_chain.chain_balance().await);
    // TODO: reserve should equal to balance ?
    assert_eq!(Amount::from_attos(19897714379699202921), pool.reserve_1);
    assert_eq!(Amount::from_attos(221085715329991143570652), pool.reserve_0);

    let query = format!("query {{ balanceOf(owner: \"{}\")}}", user_account);
    let QueryOutcome { response, .. } = meme_chain
        .graphql_query(suite.meme_application_id.unwrap(), query)
        .await;
    assert_eq!(
        Amount::from_str(response["balanceOf"].as_str().unwrap()).unwrap(),
        Amount::from_attos(10778914284670008856429348),
    );

    let query = format!("query {{ liquidity(owner: \"{}\")}}", user_account);
    let QueryOutcome { response, .. } = pool_chain
        .graphql_query(suite.pool_application_id.unwrap(), query)
        .await;
    assert_eq!(
        Amount::from_str(response["liquidity"].as_str().unwrap()).unwrap(),
        Amount::from_attos(10299999999999999981),
    );
}

#[tokio::test(flavor = "multi_thread")]
async fn pool_real_initial_liquidity_test() {
    let _ = env_logger::builder().is_test(true).try_init();

    let mut suite = TestSuite::new().await;
    let meme_chain = &suite.meme_chain.clone();
    let swap_chain = &suite.swap_chain.clone();

    let swap_key_pair = swap_chain.key_pair();

    suite
        .fund_chain(
            &meme_chain,
            OPEN_CHAIN_FEE_BUDGET.try_add(suite.initial_native).unwrap(),
        )
        .await;

    suite.create_swap_application().await;
    suite.create_meme_application(false).await;

    // Check initial swap pool
    meme_chain.handle_received_messages().await;
    swap_chain.handle_received_messages().await;

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
    suite.pool_chain = Some(pool_chain.clone());

    pool_chain.handle_received_messages().await;
    swap_chain.handle_received_messages().await;
    meme_chain.handle_received_messages().await;
    // Process messages generated by meme application
    swap_chain.handle_received_messages().await;
    pool_chain.handle_received_messages().await;

    let QueryOutcome { response, .. } = swap_chain
        .graphql_query(
            suite.swap_application_id.unwrap(),
            "query { pools {
                poolId
                token0
                token1
                poolApplication
            } }",
        )
        .await;
    assert_eq!(response["pools"].as_array().unwrap().len(), 1,);
    let pool: PoolIndex =
        serde_json::from_value(response["pools"].as_array().unwrap()[0].clone()).unwrap();

    let Some(AccountOwner::Application(pool_application_id)) = pool.pool_application.owner else {
        panic!("Invalid pool application");
    };
    suite.pool_application_id = Some(pool_application_id.with_abi::<PoolAbi>());

    let QueryOutcome { response, .. } = pool_chain
        .graphql_query(suite.pool_application_id.unwrap(), "query { pool }")
        .await;
    let pool: Pool = serde_json::from_value(response["pool"].clone()).unwrap();

    assert_eq!(OPEN_CHAIN_FEE_BUDGET, pool_chain.chain_balance().await);
    assert_eq!(
        suite.initial_native,
        pool_chain
            .owner_balance(&AccountOwner::Application(pool_application_id))
            .await
            .unwrap()
    );
    assert_eq!(suite.initial_native, pool.reserve_1);
    assert_eq!(suite.initial_liquidity, pool.reserve_0);

    let pool_application_account = suite.application_account(
        pool_chain.id(),
        suite.pool_application_id.unwrap().forget_abi(),
    );
    let query = format!(
        "query {{ balanceOf(owner: \"{}\")}}",
        pool_application_account,
    );
    let QueryOutcome { response, .. } = meme_chain
        .graphql_query(suite.meme_application_id.unwrap(), query)
        .await;
    assert_eq!(
        Amount::from_str(response["balanceOf"].as_str().unwrap()).unwrap(),
        suite.initial_liquidity,
    );
}
