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
        pool::{InstantiationArgument as PoolInstantiationArgument, Pool, PoolAbi, PoolParameters},
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
    let swap_chain = &suite.swap_chain.clone();

    let swap_key_pair = swap_chain.key_pair();

    suite.fund_chain(&meme_chain, OPEN_CHAIN_FEE_BUDGET).await;

    suite.create_swap_application().await;
    suite.create_meme_application().await;

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
    log::info!("Pool {:?}", pool);
}
