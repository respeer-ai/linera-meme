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
use std::{collections::HashMap, str::FromStr};

#[derive(Clone)]
struct TestSuite {
    validator: TestValidator,

    admin_chain: ActiveChain,
    meme_chain_0: ActiveChain,
    meme_chain_1: ActiveChain,
    user_chain: ActiveChain,
    pool_chain_meme_0: Option<ActiveChain>,
    pool_chain_meme_1: Option<ActiveChain>,
    pool_chain_user: Option<ActiveChain>,
    swap_chain: ActiveChain,

    pool_bytecode_id: ModuleId<PoolAbi, PoolParameters, PoolInstantiationArgument>,
    pool_application_id_meme_0: Option<ApplicationId<PoolAbi>>,
    pool_application_id_meme_1: Option<ApplicationId<PoolAbi>>,
    pool_application_id_user: Option<ApplicationId<PoolAbi>>,
    meme_application_id_0: Option<ApplicationId<MemeAbi>>,
    meme_application_id_1: Option<ApplicationId<MemeAbi>>,
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
        let meme_chain_0 = validator.new_chain().await;
        let meme_chain_1 = validator.new_chain().await;
        let user_chain = validator.new_chain().await;
        let swap_chain = validator.new_chain().await;

        TestSuite {
            validator,

            admin_chain,
            meme_chain_0,
            meme_chain_1,
            user_chain,
            pool_chain_meme_0: None,
            pool_chain_meme_1: None,
            pool_chain_user: None,
            swap_chain,

            pool_bytecode_id,
            pool_application_id_meme_0: None,
            pool_application_id_meme_1: None,
            pool_application_id_user: None,
            meme_application_id_0: None,
            meme_application_id_1: None,
            swap_application_id: None,

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
            creator: self.chain_owner_account(&self.meme_chain_0),
            initial_liquidity: Some(Liquidity {
                fungible_amount: self.initial_liquidity,
                native_amount: self.initial_native,
            }),
            virtual_initial_liquidity,
            swap_creator_chain_id: self.swap_chain.id(),
        };

        let meme_bytecode_id = self.meme_chain_0.publish_bytecode_files_in("../meme").await;
        self.meme_application_id_0 = Some(
            self.meme_chain_0
                .create_application(
                    meme_bytecode_id,
                    parameters.clone(),
                    instantiation_argument.clone(),
                    vec![],
                )
                .await,
        );

        let parameters = MemeParameters {
            creator: self.chain_owner_account(&self.meme_chain_1),
            initial_liquidity: Some(Liquidity {
                fungible_amount: self.initial_liquidity,
                native_amount: self.initial_native,
            }),
            virtual_initial_liquidity,
            swap_creator_chain_id: self.swap_chain.id(),
        };
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
    }

    async fn swap(
        &self,
        chain: &ActiveChain,
        pool_chain: &ActiveChain,
        pool_application_id: ApplicationId<PoolAbi>,
        buy_token_0: bool,
        amount: Amount,
    ) {
        chain
            .add_block(|block| {
                block.with_operation(
                    pool_application_id,
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
        self.meme_chain_0.handle_received_messages().await;
        self.meme_chain_1.handle_received_messages().await;
        chain.handle_received_messages().await;
        pool_chain.handle_received_messages().await;
        pool_chain.handle_received_messages().await;
        self.meme_chain_0.handle_received_messages().await;
        self.meme_chain_1.handle_received_messages().await;
        chain.handle_received_messages().await;
    }

    async fn add_liquidity(
        &self,
        chain: &ActiveChain,
        pool_chain: &ActiveChain,
        pool_application_id: ApplicationId<PoolAbi>,
        amount_0: Amount,
        amount_1: Amount,
    ) {
        chain
            .add_block(|block| {
                block.with_operation(
                    pool_application_id,
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

        self.meme_chain_0.handle_received_messages().await;
        self.meme_chain_1.handle_received_messages().await;
        chain.handle_received_messages().await;
        chain.handle_received_messages().await;
        chain.handle_received_messages().await;
        pool_chain.handle_received_messages().await;
        pool_chain.handle_received_messages().await;
        chain.handle_received_messages().await;

        self.meme_chain_0.handle_received_messages().await;
        self.meme_chain_1.handle_received_messages().await;
        chain.handle_received_messages().await;
        chain.handle_received_messages().await;
        chain.handle_received_messages().await;
        pool_chain.handle_received_messages().await;
        pool_chain.handle_received_messages().await;
        chain.handle_received_messages().await;

        self.meme_chain_0.handle_received_messages().await;
        self.meme_chain_1.handle_received_messages().await;
        chain.handle_received_messages().await;
        chain.handle_received_messages().await;
        chain.handle_received_messages().await;
        pool_chain.handle_received_messages().await;
        pool_chain.handle_received_messages().await;
        chain.handle_received_messages().await;
    }

    async fn create_pool(&self, chain: &ActiveChain, amount_0: Amount, amount_1: Amount) {
        chain
            .add_block(|block| {
                block.with_operation(
                    self.swap_application_id.unwrap(),
                    SwapOperation::CreatePool {
                        token_0_creator_chain_id: chain.id(),
                        token_0: self.meme_application_id_0.unwrap().forget_abi(),
                        token_1_creator_chain_id: Some(chain.id()),
                        token_1: Some(self.meme_application_id_1.unwrap().forget_abi()),
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
        self.meme_chain_0.handle_received_messages().await;
        self.meme_chain_1.handle_received_messages().await;
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
    let meme_chain_0 = &suite.meme_chain_0.clone();
    let meme_chain_1 = &suite.meme_chain_1.clone();
    let user_chain = &suite.user_chain.clone();
    let swap_chain = &suite.swap_chain.clone();

    let swap_key_pair = swap_chain.key_pair();

    suite.fund_chain(&meme_chain_0, OPEN_CHAIN_FEE_BUDGET).await;
    suite.fund_chain(&meme_chain_1, OPEN_CHAIN_FEE_BUDGET).await;
    suite
        .fund_chain(
            &user_chain,
            OPEN_CHAIN_FEE_BUDGET
                .try_add(Amount::from_tokens(10))
                .unwrap(),
        )
        .await;

    suite.create_swap_application().await;
    suite.create_meme_applications(true).await;

    // Check initial swap pool
    meme_chain_0.handle_received_messages().await;
    meme_chain_1.handle_received_messages().await;
    swap_chain.handle_received_messages().await;

    let mut maintained_chains = HashMap::new();
    let QueryOutcome { response, .. } = swap_chain
        .graphql_query(
            suite.swap_application_id.unwrap(),
            "query { poolChainCreationMessages }",
        )
        .await;
    for message in response["poolChainCreationMessages"].as_array().unwrap() {
        let message_id = MessageId::from_str(message.as_str().unwrap()).unwrap();
        let description = ChainDescription::Child(message_id);
        let pool_chain =
            ActiveChain::new(swap_key_pair.copy(), description, suite.clone().validator);
        pool_chain.handle_received_messages().await;
        suite.validator.add_chain(pool_chain.clone());
        maintained_chains.insert(pool_chain.id(), true);
    }

    suite.swap_chain.handle_received_messages().await;

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
    assert_eq!(response["pools"].as_array().unwrap().len(), 2);

    let pools: Vec<PoolIndex> = serde_json::from_value(response["pools"].clone()).unwrap();
    for pool in pools {
        let AccountOwner::Address32(application_description_hash) = pool.pool_application.owner
        else {
            panic!("Invalid pool application");
        };
        let pool_application_id = ApplicationId::new(application_description_hash);
        if pool.token_0 == suite.meme_application_id_0.unwrap().forget_abi()
            && pool.token_1.is_none()
        {
            suite.pool_application_id_meme_0 = Some(pool_application_id.with_abi::<PoolAbi>());
            suite.pool_chain_meme_0 =
                Some(suite.validator.get_chain(&pool.pool_application.chain_id));
        } else if pool.token_0 == suite.meme_application_id_1.unwrap().forget_abi()
            && pool.token_1.is_none()
        {
            suite.pool_application_id_meme_1 = Some(pool_application_id.with_abi::<PoolAbi>());
            suite.pool_chain_meme_1 =
                Some(suite.validator.get_chain(&pool.pool_application.chain_id));
        }
    }

    let pool_chain_meme_0 = &suite.pool_chain_meme_0.as_ref().unwrap().clone();
    let pool_chain_meme_1 = &suite.pool_chain_meme_1.as_ref().unwrap().clone();
    suite
        .swap(
            &user_chain,
            &pool_chain_meme_0,
            suite.pool_application_id_meme_0.unwrap(),
            true,
            Amount::from_str("0.78").unwrap(),
        )
        .await;

    let user_account = suite.chain_owner_account(user_chain);
    let query = format!("query {{ balanceOf(owner: \"{}\")}}", user_account);
    let QueryOutcome { response, .. } = meme_chain_0
        .graphql_query(suite.meme_application_id_0.unwrap(), query.clone())
        .await;
    assert_eq!(
        Amount::from_str(response["balanceOf"].as_str().unwrap()).unwrap(),
        Amount::from_attos(858000000000000000000000),
    );

    suite
        .swap(
            &user_chain,
            &pool_chain_meme_1,
            suite.pool_application_id_meme_1.unwrap(),
            true,
            Amount::from_str("1.23").unwrap(),
        )
        .await;

    let QueryOutcome { response, .. } = meme_chain_1
        .graphql_query(suite.meme_application_id_1.unwrap(), query)
        .await;
    assert_eq!(
        Amount::from_str(response["balanceOf"].as_str().unwrap()).unwrap(),
        Amount::from_attos(1353000000000000000000000),
    );

    suite
        .create_pool(&user_chain, Amount::ONE, Amount::ONE)
        .await;

    let QueryOutcome { response, .. } = swap_chain
        .graphql_query(
            suite.swap_application_id.unwrap(),
            "query { poolChainCreationMessages }",
        )
        .await;
    for message in response["poolChainCreationMessages"].as_array().unwrap() {
        let message_id = MessageId::from_str(message.as_str().unwrap()).unwrap();
        let description = ChainDescription::Child(message_id);
        let pool_chain =
            ActiveChain::new(swap_key_pair.copy(), description, suite.clone().validator);
        pool_chain.handle_received_messages().await;

        if maintained_chains.contains_key(&pool_chain.id()) {
            continue;
        }

        suite.validator.add_chain(pool_chain.clone());
        maintained_chains.insert(pool_chain.id(), true);
    }

    suite.swap_chain.handle_received_messages().await;

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
    assert_eq!(response["pools"].as_array().unwrap().len(), 3);

    let pools: Vec<PoolIndex> = serde_json::from_value(response["pools"].clone()).unwrap();
    for pool in pools {
        let AccountOwner::Address32(application_description_hash) = pool.pool_application.owner
        else {
            panic!("Invalid pool application");
        };
        let pool_application_id = ApplicationId::new(application_description_hash);
        if pool.token_0 == suite.meme_application_id_0.unwrap().forget_abi()
            && pool.token_1 == Some(suite.meme_application_id_1.unwrap().forget_abi())
        {
            suite.pool_application_id_user = Some(pool_application_id.with_abi::<PoolAbi>());
            suite.pool_chain_user =
                Some(suite.validator.get_chain(&pool.pool_application.chain_id));
            break;
        }
    }

    let pool_chain_user = &suite.pool_chain_user.as_ref().unwrap().clone();

    let pool_application_account = suite.application_account(
        pool_chain_user.id(),
        suite.pool_application_id_user.unwrap().forget_abi(),
    );

    pool_chain_meme_0.handle_received_messages().await;
    pool_chain_meme_1.handle_received_messages().await;
    pool_chain_user.handle_received_messages().await;

    meme_chain_0.handle_received_messages().await;
    meme_chain_1.handle_received_messages().await;

    swap_chain.handle_received_messages().await;
    user_chain.handle_received_messages().await;

    pool_chain_meme_0.handle_received_messages().await;
    pool_chain_meme_1.handle_received_messages().await;
    pool_chain_user.handle_received_messages().await;

    meme_chain_0.handle_received_messages().await;
    meme_chain_1.handle_received_messages().await;

    swap_chain.handle_received_messages().await;
    user_chain.handle_received_messages().await;
    pool_chain_user.handle_received_messages().await;

    meme_chain_0.handle_received_messages().await;
    meme_chain_1.handle_received_messages().await;

    swap_chain.handle_received_messages().await;
    user_chain.handle_received_messages().await;
    pool_chain_user.handle_received_messages().await;
    user_chain.handle_received_messages().await;

    meme_chain_0.handle_received_messages().await;
    meme_chain_1.handle_received_messages().await;

    swap_chain.handle_received_messages().await;
    user_chain.handle_received_messages().await;
    pool_chain_user.handle_received_messages().await;

    let QueryOutcome { response, .. } = pool_chain_user
        .graphql_query(suite.pool_application_id_user.unwrap(), "query { pool }")
        .await;
    let pool: Pool = serde_json::from_value(response["pool"].clone()).unwrap();

    assert_eq!(OPEN_CHAIN_FEE_BUDGET, pool_chain_user.chain_balance().await);
    assert_eq!(Amount::ONE, pool.reserve_0);
    assert_eq!(Amount::ONE, pool.reserve_1);

    let query = format!(
        "query {{ balanceOf(owner: \"{}\")}}",
        pool_application_account
    );
    let QueryOutcome { response, .. } = meme_chain_0
        .graphql_query(suite.meme_application_id_0.unwrap(), query.clone())
        .await;
    assert_eq!(
        Amount::from_str(response["balanceOf"].as_str().unwrap()).unwrap(),
        Amount::ONE,
    );

    let QueryOutcome { response, .. } = meme_chain_1
        .graphql_query(suite.meme_application_id_1.unwrap(), query.clone())
        .await;
    assert_eq!(
        Amount::from_str(response["balanceOf"].as_str().unwrap()).unwrap(),
        Amount::ONE,
    );

    suite
        .swap(
            &user_chain,
            &pool_chain_user,
            suite.pool_application_id_user.unwrap(),
            true,
            Amount::from_str("0.2").unwrap(),
        )
        .await;

    user_chain.handle_received_messages().await;
    pool_chain_user.handle_received_messages().await;
    meme_chain_0.handle_received_messages().await;
    meme_chain_1.handle_received_messages().await;

    user_chain.handle_received_messages().await;
    pool_chain_user.handle_received_messages().await;
    user_chain.handle_received_messages().await;

    let QueryOutcome { response, .. } = meme_chain_0
        .graphql_query(suite.meme_application_id_0.unwrap(), query.clone())
        .await;
    assert_eq!(
        Amount::from_str(response["balanceOf"].as_str().unwrap()).unwrap(),
        Amount::from_str("0.8").unwrap(),
    );

    let QueryOutcome { response, .. } = meme_chain_1
        .graphql_query(suite.meme_application_id_1.unwrap(), query.clone())
        .await;
    assert_eq!(
        Amount::from_str(response["balanceOf"].as_str().unwrap()).unwrap(),
        Amount::from_str("1.2").unwrap(),
    );

    let query = format!("query {{ balanceOf(owner: \"{}\")}}", user_account);

    let QueryOutcome { response, .. } = meme_chain_0
        .graphql_query(suite.meme_application_id_0.unwrap(), query.clone())
        .await;
    assert_eq!(
        Amount::from_str(response["balanceOf"].as_str().unwrap()).unwrap(),
        Amount::from_attos(857999200000000000000000),
    );

    let QueryOutcome { response, .. } = meme_chain_1
        .graphql_query(suite.meme_application_id_1.unwrap(), query.clone())
        .await;
    assert_eq!(
        Amount::from_str(response["balanceOf"].as_str().unwrap()).unwrap(),
        Amount::from_attos(1352998800000000000000000),
    );

    suite
        .add_liquidity(
            &user_chain,
            &pool_chain_user,
            suite.pool_application_id_user.unwrap(),
            Amount::from_str("1.2").unwrap(),
            Amount::from_str("1.8").unwrap(),
        )
        .await;

    let query = format!(
        "query {{ balanceOf(owner: \"{}\")}}",
        pool_application_account
    );

    let QueryOutcome { response, .. } = meme_chain_0
        .graphql_query(suite.meme_application_id_0.unwrap(), query.clone())
        .await;
    assert_eq!(
        Amount::from_str(response["balanceOf"].as_str().unwrap()).unwrap(),
        Amount::from_str("2.0").unwrap(),
    );

    let QueryOutcome { response, .. } = meme_chain_1
        .graphql_query(suite.meme_application_id_1.unwrap(), query.clone())
        .await;
    assert_eq!(
        Amount::from_str(response["balanceOf"].as_str().unwrap()).unwrap(),
        Amount::from_tokens(3),
    );

    let query = format!("query {{ balanceOf(owner: \"{}\")}}", user_account);

    let QueryOutcome { response, .. } = meme_chain_0
        .graphql_query(suite.meme_application_id_0.unwrap(), query.clone())
        .await;
    assert_eq!(
        Amount::from_str(response["balanceOf"].as_str().unwrap()).unwrap(),
        Amount::from_attos(857998000000000000000000),
    );

    let QueryOutcome { response, .. } = meme_chain_1
        .graphql_query(suite.meme_application_id_1.unwrap(), query.clone())
        .await;
    assert_eq!(
        Amount::from_str(response["balanceOf"].as_str().unwrap()).unwrap(),
        Amount::from_attos(1352997000000000000000000),
    );

    let QueryOutcome { response, .. } = pool_chain_user
        .graphql_query(suite.pool_application_id_user.unwrap(), "query { pool }")
        .await;
    let pool: Pool = serde_json::from_value(response["pool"].clone()).unwrap();

    assert_eq!(OPEN_CHAIN_FEE_BUDGET, pool_chain_user.chain_balance().await);
    assert_eq!(Amount::from_tokens(3), pool.reserve_1);
    assert_eq!(Amount::from_tokens(2), pool.reserve_0);
}
