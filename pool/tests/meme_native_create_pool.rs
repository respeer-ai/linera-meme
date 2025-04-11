// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

//! Integration tests for the Pool application.

#![cfg(not(target_arch = "wasm32"))]

use abi::{
    meme::{
        InstantiationArgument as MemeInstantiationArgument, Meme, MemeAbi, MemeParameters, Metadata,
    },
    policy::open_chain_fee_budget,
    store_type::StoreType,
    swap::{
        pool::{
            InstantiationArgument as PoolInstantiationArgument, Pool, PoolAbi, PoolOperation,
            PoolParameters,
        },
        router::{
            InstantiationArgument as SwapInstantiationArgument, Pool as PoolIndex, SwapAbi,
            SwapOperation, SwapParameters,
        },
    },
};
use linera_sdk::{
    linera_base_types::{
        Account, AccountOwner, Amount, ApplicationId, ChainDescription, ChainId, CryptoHash,
        MessageId, ModuleId, TestString,
    },
    test::{ActiveChain, Medium, MessageAction, QueryOutcome, Recipient, TestValidator},
};
use pool::LiquidityAmount;
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
            initial_liquidity: Amount::from_tokens(10),
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
                    logo: Some(CryptoHash::new(&TestString::new("Test Logo".to_string()))),
                    description: "Test token description".to_string(),
                    twitter: None,
                    telegram: None,
                    discord: None,
                    website: None,
                    github: None,
                    live_stream: None,
                },
                virtual_initial_liquidity: true,
                initial_liquidity: None,
            },
            blob_gateway_application_id: None,
            ams_application_id: None,
            proxy_application_id: None,
            swap_application_id: Some(self.swap_application_id.unwrap().forget_abi()),
        };
        let parameters = MemeParameters {
            creator: self.chain_owner_account(&self.meme_chain),
            initial_liquidity: None,
            virtual_initial_liquidity: true,
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

    async fn swap(&self, chain: &ActiveChain, buy_token_0: bool, amount: Amount) {
        chain
            .add_block(|block| {
                block.with_operation(
                    self.pool_application_id.unwrap(),
                    PoolOperation::Swap {
                        amount_0_in: if buy_token_0 { None } else { Some(amount) },
                        amount_1_in: if buy_token_0 { Some(amount) } else { None },
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
        self.swap_chain.handle_received_messages().await;
        chain.handle_received_messages().await;
    }

    async fn create_pool(&self, chain: &ActiveChain, amount_0: Amount, amount_1: Amount) {
        chain
            .add_block(|block| {
                block.with_operation(
                    self.swap_application_id.unwrap(),
                    SwapOperation::CreatePool {
                        token_0_creator_chain_id: self.meme_chain.id(),
                        token_0: self.meme_application_id.unwrap().forget_abi(),
                        token_1_creator_chain_id: None,
                        token_1: None,
                        amount_0,
                        amount_1,
                        to: None,
                    },
                );
            })
            .await;
        self.swap_chain.handle_received_messages().await;
        chain.handle_received_messages().await;
        chain.handle_received_messages().await;
        chain.handle_received_messages().await;
        self.meme_chain.handle_received_messages().await;
        self.swap_chain.handle_received_messages().await;
        self.meme_chain.handle_received_messages().await;
        chain.handle_received_messages().await;
        self.swap_chain.handle_received_messages().await;
        self.meme_chain.handle_received_messages().await;
        chain.handle_received_messages().await;
        self.swap_chain.handle_received_messages().await;
        self.meme_chain.handle_received_messages().await;
        chain.handle_received_messages().await;
        self.swap_chain.handle_received_messages().await;
        self.meme_chain.handle_received_messages().await;
        chain.handle_received_messages().await;
    }
}

/// Test setting a pool and testing its coherency across microchains.
///
/// Creates the application on a `chain`, initializing it with a 42 then adds 15 and obtains 57.
/// which is then checked.
#[tokio::test(flavor = "multi_thread")]
async fn meme_native_create_pool_test() {
    let _ = env_logger::builder().is_test(true).try_init();

    let mut suite = TestSuite::new().await;
    let meme_chain = &suite.meme_chain.clone();
    let user_chain = &suite.user_chain.clone();
    let swap_chain = &suite.swap_chain.clone();

    let swap_key_pair = swap_chain.key_pair();

    suite
        .fund_chain(
            &meme_chain,
            open_chain_fee_budget()
                .try_add(suite.initial_native)
                .unwrap(),
        )
        .await;

    suite.create_swap_application().await;
    suite.create_meme_application().await;

    // Check initial swap pool
    meme_chain.handle_received_messages().await;
    swap_chain.handle_received_messages().await;

    // Create pool
    suite
        .create_pool(&meme_chain, suite.initial_liquidity, suite.initial_native)
        .await;

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
    pool_chain.handle_received_messages().await;
    swap_chain.handle_received_messages().await;
    meme_chain.handle_received_messages().await;
    pool_chain.handle_received_messages().await;
    swap_chain.handle_received_messages().await;
    meme_chain.handle_received_messages().await;
    pool_chain.handle_received_messages().await;
    swap_chain.handle_received_messages().await;
    meme_chain.handle_received_messages().await;

    let QueryOutcome { response, .. } = swap_chain
        .graphql_query(
            suite.swap_application_id.unwrap(),
            "query { pools {
                creator
                poolId
                token0
                token1
                poolApplication
            } }",
        )
        .await;
    assert_eq!(response["pools"].as_array().unwrap().len(), 1);
    let pool: PoolIndex =
        serde_json::from_value(response["pools"].as_array().unwrap()[0].clone()).unwrap();

    let AccountOwner::Address32(application_description_hash) = pool.pool_application.owner else {
        panic!("Invalid pool application");
    };
    let pool_application_id = ApplicationId::new(application_description_hash);
    suite.pool_application_id = Some(pool_application_id.with_abi::<PoolAbi>());

    let QueryOutcome { response, .. } = pool_chain
        .graphql_query(suite.pool_application_id.unwrap(), "query { pool }")
        .await;
    let pool: Pool = serde_json::from_value(response["pool"].clone()).unwrap();

    assert_eq!(open_chain_fee_budget(), pool_chain.chain_balance().await);
    assert_eq!(suite.initial_liquidity, pool.reserve_0);
    assert_eq!(suite.initial_native, pool.reserve_1);

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
    suite.swap(&user_chain, true, budget).await;

    assert_eq!(
        balance.try_sub(budget).unwrap(),
        user_chain.chain_balance().await
    );
    assert_eq!(open_chain_fee_budget(), pool_chain.chain_balance().await);
    assert_eq!(
        budget.try_add(suite.initial_native).unwrap(),
        pool_chain
            .owner_balance(&AccountOwner::from(pool_application_id))
            .await
            .unwrap()
    );

    let QueryOutcome { response, .. } = pool_chain
        .graphql_query(suite.pool_application_id.unwrap(), "query { pool }")
        .await;
    let pool: Pool = serde_json::from_value(response["pool"].clone()).unwrap();

    assert_eq!(open_chain_fee_budget(), pool_chain.chain_balance().await);
    assert_eq!(Amount::from_attos(19800000000000000000), pool.reserve_1);
    assert_eq!(Amount::from_attos(200000000000000000), pool.reserve_0);

    let user_account = suite.chain_owner_account(&user_chain);
    let query = format!("query {{ balanceOf(owner: \"{}\")}}", user_account);
    let QueryOutcome { response, .. } = meme_chain
        .graphql_query(suite.meme_application_id.unwrap(), query)
        .await;
    assert_eq!(
        Amount::from_str(response["balanceOf"].as_str().unwrap()).unwrap(),
        Amount::from_attos(9800000000000000000),
    );

    let query = format!(
        "query {{ balanceOf(owner: \"{}\")}}",
        pool_application_account,
    );
    let QueryOutcome { response, .. } = meme_chain
        .graphql_query(suite.meme_application_id.unwrap(), query.clone())
        .await;
    assert_eq!(
        Amount::from_str(response["balanceOf"].as_str().unwrap()).unwrap(),
        Amount::from_attos(200000000000000000),
    );

    let liquidity_fund_amount = Amount::from_attos(19800000000000000000);
    assert_eq!(
        liquidity_fund_amount,
        pool_chain
            .owner_balance(&AccountOwner::from(pool_application_id))
            .await
            .unwrap()
    );

    // Here meme balance should already add to pool application
    let QueryOutcome { response, .. } = meme_chain
        .graphql_query(suite.meme_application_id.unwrap(), query)
        .await;
    assert_eq!(
        Amount::from_str(response["balanceOf"].as_str().unwrap()).unwrap(),
        Amount::from_attos(200000000000000000),
    );

    let QueryOutcome { response, .. } = pool_chain
        .graphql_query(suite.pool_application_id.unwrap(), "query { pool }")
        .await;
    let pool: Pool = serde_json::from_value(response["pool"].clone()).unwrap();

    assert_eq!(open_chain_fee_budget(), pool_chain.chain_balance().await);
    // TODO: reserve should equal to balance ?
    assert_eq!(Amount::from_attos(19800000000000000000), pool.reserve_1);
    assert_eq!(Amount::from_attos(200000000000000000), pool.reserve_0);

    let query = format!("query {{ balanceOf(owner: \"{}\")}}", user_account);
    let QueryOutcome { response, .. } = meme_chain
        .graphql_query(suite.meme_application_id.unwrap(), query)
        .await;
    assert_eq!(
        Amount::from_str(response["balanceOf"].as_str().unwrap()).unwrap(),
        Amount::from_attos(9800000000000000000),
    );

    let meme_account = suite.chain_owner_account(&meme_chain);
    let query = format!(
        "query {{ liquidity(owner: \"{}\") {{
        liquidity
        amount0
        amount1
    }} }}",
        meme_account
    );
    let QueryOutcome { response, .. } = pool_chain
        .graphql_query(suite.pool_application_id.unwrap(), query)
        .await;
    let liquidity: LiquidityAmount = serde_json::from_value(response["liquidity"].clone()).unwrap();
    assert_eq!(
        liquidity.liquidity,
        Amount::from_attos(10000000000000000000),
    );
}
