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
    swap::router::{
        InstantiationArgument as SwapInstantiationArgument, SwapAbi, SwapOperation, SwapParameters,
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
    validator: TestValidator,

    admin_chain: ActiveChain,
    meme_chain: ActiveChain,
    user_chain: ActiveChain,
    swap_chain: ActiveChain,

    swap_bytecode_id: ModuleId<SwapAbi, SwapParameters, SwapInstantiationArgument>,
    meme_application_id: Option<ApplicationId<MemeAbi>>,
    swap_application_id: Option<ApplicationId<SwapAbi>>,

    initial_supply: Amount,
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
        let user_chain = validator.new_chain().await;
        let swap_chain = validator.new_chain().await;

        TestSuite {
            validator,

            admin_chain,
            meme_chain,
            user_chain,
            swap_chain,

            swap_bytecode_id,
            meme_application_id: None,
            swap_application_id: None,

            initial_supply: Amount::from_tokens(21000000),
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
        );
    }

    async fn create_pool(&self, chain: &ActiveChain, amount_0: Amount, amount_1: Amount) {
        chain
            .add_block(|block| {
                block.with_operation(
                    self.swap_application_id.unwrap(),
                    SwapOperation::CreatePool {
                        token_0_creator_chain_id: chain.id(),
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
    }
}

/// Test setting a pool and testing its coherency across microchains.
///
/// Creates the application on a `chain`, initializing it with a 42 then adds 15 and obtains 57.
/// which is then checked.
#[tokio::test(flavor = "multi_thread")]
async fn meme_native_pair_without_initial_liquidity_test() {
    let _ = env_logger::builder().is_test(true).try_init();

    let mut suite = TestSuite::new().await;
    let meme_chain = &suite.meme_chain.clone();
    let user_chain = &suite.user_chain.clone();
    let swap_chain = &suite.swap_chain.clone();

    let swap_key_pair = swap_chain.key_pair();

    suite
        .fund_chain(&meme_chain, open_chain_fee_budget().try_mul(2).unwrap())
        .await;
    suite
        .fund_chain(
            &user_chain,
            open_chain_fee_budget()
                .try_add(Amount::from_tokens(10))
                .unwrap(),
        )
        .await;

    suite.create_swap_application().await;
    suite.create_meme_application().await;

    // Check initial swap pool
    meme_chain.handle_received_messages().await;
    swap_chain.handle_received_messages().await;
    swap_chain.handle_received_messages().await;

    // Only meme chain has meme balance right now
    suite
        .create_pool(&meme_chain, Amount::ONE, Amount::ONE)
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
        1
    );

    let message_id = MessageId::from_str(
        response["poolChainCreationMessages"].as_array().unwrap()[0]
            .as_str()
            .unwrap(),
    )
    .unwrap();
    let description = ChainDescription::Child(message_id);
    let pool_chain = ActiveChain::new(swap_key_pair.copy(), description, suite.clone().validator);
    pool_chain.handle_received_messages().await;

    suite.validator.add_chain(pool_chain.clone());

    swap_chain.handle_received_messages().await;

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
            } }",
        )
        .await;
    assert_eq!(response["pools"].as_array().unwrap().len(), 1);

    pool_chain.handle_received_messages().await;
    meme_chain.handle_received_messages().await;
    swap_chain.handle_received_messages().await;

    // TODO: transfer one to user then create pool
}
