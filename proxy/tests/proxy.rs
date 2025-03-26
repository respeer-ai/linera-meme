// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

//! Integration tests for the Proxy application.

#![cfg(not(target_arch = "wasm32"))]

use abi::{
    constant::OPEN_CHAIN_FEE_BUDGET,
    meme::{
        InstantiationArgument as MemeInstantiationArgument, Liquidity, Meme, MemeParameters,
        Metadata,
    },
    proxy::{InstantiationArgument, ProxyAbi, ProxyOperation},
    store_type::StoreType,
    swap::router::{InstantiationArgument as SwapInstantiationArgument, SwapAbi, SwapParameters},
};
use linera_sdk::{
    linera_base_types::{
        Account, AccountOwner, AccountSecretKey, Amount, ApplicationId, ChainDescription, ChainId,
        CryptoHash, Ed25519SecretKey, MessageId, ModuleId, Owner, TestString, TimeoutConfig,
    },
    test::{ActiveChain, Medium, MessageAction, QueryOutcome, Recipient, TestValidator},
};
use serde_json::json;
use std::str::FromStr;

#[derive(Clone)]
struct TestSuite {
    pub validator: TestValidator,

    pub admin_chain: ActiveChain,
    pub proxy_chain: ActiveChain,
    pub meme_user_chain: ActiveChain,
    pub operator_chain_1: ActiveChain,
    pub operator_chain_2: ActiveChain,
    pub swap_chain: ActiveChain,

    pub proxy_bytecode_id: ModuleId<ProxyAbi, (), InstantiationArgument>,
    pub meme_bytecode_id: ModuleId,
    pub proxy_application_id: Option<ApplicationId<ProxyAbi>>,
    pub swap_application_id: Option<ApplicationId<SwapAbi>>,

    pub initial_liquidity: Amount,
    pub initial_native: Amount,
}

impl TestSuite {
    async fn new() -> Self {
        let (validator, proxy_bytecode_id) =
            TestValidator::with_current_module::<ProxyAbi, (), InstantiationArgument>().await;

        let admin_chain = validator.get_chain(&ChainId::root(0));
        let proxy_chain = validator.new_chain().await;
        let meme_user_chain = validator.new_chain().await;
        let operator_chain_1 = validator.new_chain().await;
        let operator_chain_2 = validator.new_chain().await;
        let swap_chain = validator.new_chain().await;

        let meme_bytecode_id = proxy_chain.publish_bytecode_files_in("../meme").await;

        Self {
            validator,

            admin_chain,
            proxy_chain,
            meme_user_chain,
            operator_chain_1,
            operator_chain_2,
            swap_chain,

            proxy_bytecode_id,
            meme_bytecode_id,
            proxy_application_id: None,
            swap_application_id: None,

            initial_liquidity: Amount::from_tokens(11000000),
            initial_native: Amount::from_tokens(10),
        }
    }

    async fn create_proxy_application(&mut self, operators: Vec<Account>) {
        self.proxy_application_id = Some(
            self.proxy_chain
                .create_application(
                    self.proxy_bytecode_id,
                    (),
                    InstantiationArgument {
                        meme_bytecode_id: self.meme_bytecode_id,
                        operators,
                        swap_application_id: self.swap_application_id.unwrap().forget_abi(),
                    },
                    vec![],
                )
                .await,
        )
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
        let pool_bytecode_id = self.swap_chain.publish_bytecode_files_in("../pool").await;
        let swap_bytecode_id = self.swap_chain.publish_bytecode_files_in("../swap").await;

        self.swap_application_id = Some(
            self.swap_chain
                .create_application::<SwapAbi, SwapParameters, SwapInstantiationArgument>(
                    swap_bytecode_id,
                    SwapParameters {},
                    SwapInstantiationArgument { pool_bytecode_id },
                    vec![],
                )
                .await,
        )
    }

    async fn propose_add_genesis_miner(&self, chain: &ActiveChain, owner: Account) {
        let certificate = chain
            .add_block(|block| {
                block.with_operation(
                    self.proxy_application_id.unwrap(),
                    ProxyOperation::ProposeAddGenesisMiner { owner },
                );
            })
            .await;
        self.proxy_chain
            .add_block(move |block| {
                block.with_messages_from_by_medium(
                    &certificate,
                    &Medium::Direct,
                    MessageAction::Accept,
                );
            })
            .await;
    }

    async fn approve_add_genesis_miner(&self, chain: &ActiveChain, owner: Account) {
        let certificate = chain
            .add_block(|block| {
                block.with_operation(
                    self.proxy_application_id.unwrap(),
                    ProxyOperation::ApproveAddGenesisMiner { owner },
                );
            })
            .await;
        self.proxy_chain
            .add_block(move |block| {
                block.with_messages_from_by_medium(
                    &certificate,
                    &Medium::Direct,
                    MessageAction::Accept,
                );
            })
            .await;
    }

    async fn create_meme_application(&self, chain: &ActiveChain, virtual_initial_liquidity: bool) {
        let certificate = chain
            .add_block(|block| {
                block.with_operation(
                    self.proxy_application_id.unwrap(),
                    ProxyOperation::CreateMeme {
                        meme_instantiation_argument: MemeInstantiationArgument {
                            meme: Meme {
                                name: "Test Token".to_string(),
                                ticker: "LTT".to_string(),
                                decimals: 6,
                                initial_supply: Amount::from_tokens(21000000),
                                total_supply: Amount::from_tokens(21000000),
                                metadata: Metadata {
                                    logo_store_type: StoreType::S3,
                                    logo: Some(CryptoHash::new(&TestString::new(
                                        "Test Logo".to_string(),
                                    ))),
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
                            swap_application_id: Some(
                                self.swap_application_id.unwrap().forget_abi(),
                            ),
                        },
                        meme_parameters: MemeParameters {
                            creator: self.chain_owner_account(chain),
                            initial_liquidity: Some(Liquidity {
                                fungible_amount: self.initial_liquidity,
                                native_amount: self.initial_native,
                            }),
                            virtual_initial_liquidity,
                            swap_creator_chain_id: self.swap_chain.id(),
                        },
                    },
                );
            })
            .await;
        self.proxy_chain
            .add_block(move |block| {
                block.with_messages_from_by_medium(
                    &certificate,
                    &Medium::Direct,
                    MessageAction::Accept,
                );
            })
            .await;
    }

    async fn change_ownership(&self, chain: &ActiveChain, owners: Vec<Owner>) {
        chain
            .add_block(move |block| {
                block.with_owner_change(
                    Vec::new(),
                    owners.into_iter().map(|owner| (owner, 100)).collect(),
                    20,
                    false,
                    TimeoutConfig::default(),
                );
            })
            .await;
        chain.handle_received_messages().await;
    }
}

/// Test setting a proxy and testing its coherency across microchains.
///
/// Creates the application on a `chain`, initializing it with a 42 then adds 15 and obtains 57.
/// which is then checked.
#[tokio::test(flavor = "multi_thread")]
async fn proxy_create_meme_virtual_initial_liquidity_single_owner_test() {
    let _ = env_logger::builder().is_test(true).try_init();

    let mut suite = TestSuite::new().await;

    let proxy_chain = &suite.proxy_chain.clone();
    let meme_user_chain = &suite.meme_user_chain.clone();
    let operator_chain_1 = &suite.operator_chain_1.clone();
    let operator_chain_2 = &suite.operator_chain_2.clone();
    let swap_chain = &suite.swap_chain.clone();

    let proxy_owner = suite.chain_owner_account(proxy_chain);
    let operator_1 = suite.chain_owner_account(operator_chain_1);
    let operator_2 = suite.chain_owner_account(operator_chain_2);
    let meme_user_owner = suite.chain_owner_account(meme_user_chain);
    let meme_user_key_pair = meme_user_chain.key_pair();

    suite.create_swap_application().await;
    suite
        .create_proxy_application(vec![operator_1, operator_2])
        .await;

    let QueryOutcome { response, .. } = proxy_chain
        .graphql_query(
            suite.proxy_application_id.unwrap(),
            "query { memeBytecodeId }",
        )
        .await;
    let expected = json!({"memeBytecodeId": suite.meme_bytecode_id});
    assert_eq!(response, expected);

    suite
        .propose_add_genesis_miner(&operator_chain_1, meme_user_owner)
        .await;
    suite
        .approve_add_genesis_miner(&operator_chain_2, meme_user_owner)
        .await;

    let QueryOutcome { response, .. } = proxy_chain
        .graphql_query(
            suite.proxy_application_id.unwrap(),
            "query { genesisMiners }",
        )
        .await;
    let expected = json!({"genesisMiners": [proxy_owner, meme_user_owner]});
    assert_eq!(response, expected);

    suite
        .fund_chain(&meme_user_chain, OPEN_CHAIN_FEE_BUDGET)
        .await;
    suite.create_meme_application(&meme_user_chain, true).await;

    let QueryOutcome { response, .. } = proxy_chain
        .graphql_query(
            suite.proxy_application_id.unwrap(),
            "query { memeChainCreationMessages }",
        )
        .await;
    assert_eq!(
        response["memeChainCreationMessages"]
            .as_array()
            .unwrap()
            .len(),
        1
    );
    let message_id = MessageId::from_str(
        response["memeChainCreationMessages"].as_array().unwrap()[0]
            .as_str()
            .unwrap(),
    )
    .unwrap();

    let QueryOutcome { response, .. } = proxy_chain
        .graphql_query(
            suite.proxy_application_id.unwrap(),
            "query { memeApplicationIds }",
        )
        .await;
    let meme_application: Option<ApplicationId> =
        serde_json::from_value(response["memeApplicationIds"].as_array().unwrap()[0].clone())
            .unwrap();
    assert_eq!(meme_application.is_none(), true);

    let description = ChainDescription::Child(message_id);
    let meme_chain = ActiveChain::new(
        meme_user_key_pair.copy(),
        description,
        suite.clone().validator,
    );

    suite.validator.add_chain(meme_chain.clone());

    proxy_chain.handle_received_messages().await;
    meme_chain.handle_received_messages().await;
    proxy_chain.handle_received_messages().await;
    meme_chain.handle_received_messages().await;
    proxy_chain.handle_received_messages().await;
    meme_chain.handle_received_messages().await;

    let QueryOutcome { response, .. } = proxy_chain
        .graphql_query(
            suite.proxy_application_id.unwrap(),
            "query { memeApplicationIds }",
        )
        .await;
    let meme_application: Option<ApplicationId> =
        serde_json::from_value(response["memeApplicationIds"].as_array().unwrap()[0].clone())
            .unwrap();
    assert_eq!(meme_application.is_some(), true);

    proxy_chain.handle_received_messages().await;
    swap_chain.handle_received_messages().await;
    meme_chain.handle_received_messages().await;
    proxy_chain.handle_received_messages().await;
    swap_chain.handle_received_messages().await;
    meme_chain.handle_received_messages().await;
    proxy_chain.handle_received_messages().await;
    swap_chain.handle_received_messages().await;
    meme_chain.handle_received_messages().await;
}

/// Test setting a proxy and testing its coherency across microchains.
///
/// Creates the application on a `chain`, initializing it with a 42 then adds 15 and obtains 57.
/// which is then checked.
#[tokio::test(flavor = "multi_thread")]
async fn proxy_create_meme_real_initial_liquidity_single_owner_test() {
    let _ = env_logger::builder().is_test(true).try_init();

    let mut suite = TestSuite::new().await;

    let proxy_chain = &suite.proxy_chain.clone();
    let meme_user_chain = &suite.meme_user_chain.clone();
    let operator_chain_1 = &suite.operator_chain_1.clone();
    let operator_chain_2 = &suite.operator_chain_2.clone();
    let swap_chain = &suite.swap_chain.clone();

    let proxy_owner = suite.chain_owner_account(proxy_chain);
    let operator_1 = suite.chain_owner_account(operator_chain_1);
    let operator_2 = suite.chain_owner_account(operator_chain_2);
    let meme_user_owner = suite.chain_owner_account(meme_user_chain);
    let meme_user_key_pair = meme_user_chain.key_pair();

    suite.create_swap_application().await;
    suite
        .create_proxy_application(vec![operator_1, operator_2])
        .await;

    let QueryOutcome { response, .. } = proxy_chain
        .graphql_query(
            suite.proxy_application_id.unwrap(),
            "query { memeBytecodeId }",
        )
        .await;
    let expected = json!({"memeBytecodeId": suite.meme_bytecode_id});
    assert_eq!(response, expected);

    suite
        .propose_add_genesis_miner(&operator_chain_1, meme_user_owner)
        .await;
    suite
        .approve_add_genesis_miner(&operator_chain_2, meme_user_owner)
        .await;

    let QueryOutcome { response, .. } = proxy_chain
        .graphql_query(
            suite.proxy_application_id.unwrap(),
            "query { genesisMiners }",
        )
        .await;
    let expected = json!({"genesisMiners": [proxy_owner, meme_user_owner]});
    assert_eq!(response, expected);

    suite
        .fund_chain(
            &meme_user_chain,
            OPEN_CHAIN_FEE_BUDGET.try_add(suite.initial_native).unwrap(),
        )
        .await;
    suite.create_meme_application(&meme_user_chain, false).await;

    let QueryOutcome { response, .. } = proxy_chain
        .graphql_query(
            suite.proxy_application_id.unwrap(),
            "query { memeChainCreationMessages }",
        )
        .await;
    assert_eq!(
        response["memeChainCreationMessages"]
            .as_array()
            .unwrap()
            .len(),
        1
    );
    let message_id = MessageId::from_str(
        response["memeChainCreationMessages"].as_array().unwrap()[0]
            .as_str()
            .unwrap(),
    )
    .unwrap();

    let QueryOutcome { response, .. } = proxy_chain
        .graphql_query(
            suite.proxy_application_id.unwrap(),
            "query { memeApplicationIds }",
        )
        .await;
    let meme_application: Option<ApplicationId> =
        serde_json::from_value(response["memeApplicationIds"].as_array().unwrap()[0].clone())
            .unwrap();
    assert_eq!(meme_application.is_none(), true);

    let description = ChainDescription::Child(message_id);
    let meme_chain = ActiveChain::new(
        meme_user_key_pair.copy(),
        description,
        suite.clone().validator,
    );

    suite.validator.add_chain(meme_chain.clone());

    proxy_chain.handle_received_messages().await;
    meme_chain.handle_received_messages().await;
    proxy_chain.handle_received_messages().await;
    meme_chain.handle_received_messages().await;
    proxy_chain.handle_received_messages().await;
    meme_chain.handle_received_messages().await;

    let QueryOutcome { response, .. } = proxy_chain
        .graphql_query(
            suite.proxy_application_id.unwrap(),
            "query { memeApplicationIds }",
        )
        .await;
    let meme_application: Option<ApplicationId> =
        serde_json::from_value(response["memeApplicationIds"].as_array().unwrap()[0].clone())
            .unwrap();
    assert_eq!(meme_application.is_some(), true);

    proxy_chain.handle_received_messages().await;
    swap_chain.handle_received_messages().await;
    meme_chain.handle_received_messages().await;
    proxy_chain.handle_received_messages().await;
    swap_chain.handle_received_messages().await;
    meme_chain.handle_received_messages().await;
    proxy_chain.handle_received_messages().await;
    swap_chain.handle_received_messages().await;
    meme_chain.handle_received_messages().await;
}

/// Test setting a proxy and testing its coherency across microchains.
///
/// Creates the application on a `chain`, initializing it with a 42 then adds 15 and obtains 57.
/// which is then checked.
#[tokio::test(flavor = "multi_thread")]
async fn proxy_create_meme_real_initial_liquidity_multi_owner_test() {
    let _ = env_logger::builder().is_test(true).try_init();

    let mut suite = TestSuite::new().await;

    let proxy_chain = &suite.proxy_chain.clone();
    let meme_user_chain = &suite.meme_user_chain.clone();
    let operator_chain_1 = &suite.operator_chain_1.clone();
    let operator_chain_2 = &suite.operator_chain_2.clone();
    let swap_chain = &suite.swap_chain.clone();

    let operator_1 = suite.chain_owner_account(operator_chain_1);
    let operator_2 = suite.chain_owner_account(operator_chain_2);
    let meme_user_owner = suite.chain_owner_account(meme_user_chain);
    let meme_user_key_pair = meme_user_chain.key_pair();

    let proxy_key_1 = AccountSecretKey::Ed25519(Ed25519SecretKey::generate());
    let proxy_key_2 = AccountSecretKey::Ed25519(Ed25519SecretKey::generate());
    let proxy_key_3 = AccountSecretKey::Ed25519(Ed25519SecretKey::generate());
    let proxy_user_1 = Account {
        chain_id: proxy_chain.id(),
        owner: Some(AccountOwner::User(proxy_key_1.public().into())),
    };
    let proxy_user_2 = Account {
        chain_id: proxy_chain.id(),
        owner: Some(AccountOwner::User(proxy_key_2.public().into())),
    };
    let proxy_user_3 = Account {
        chain_id: proxy_chain.id(),
        owner: Some(AccountOwner::User(proxy_key_3.public().into())),
    };

    suite
        .change_ownership(
            &proxy_chain,
            [
                proxy_key_1.public().into(),
                proxy_key_2.public().into(),
                proxy_key_3.public().into(),
            ]
            .to_vec(),
        )
        .await;

    suite.create_swap_application().await;
    suite
        .create_proxy_application(vec![operator_1, operator_2])
        .await;

    let QueryOutcome { response, .. } = proxy_chain
        .graphql_query(
            suite.proxy_application_id.unwrap(),
            "query { memeBytecodeId }",
        )
        .await;
    let expected = json!({"memeBytecodeId": suite.meme_bytecode_id});
    assert_eq!(response, expected);

    suite
        .propose_add_genesis_miner(&operator_chain_1, meme_user_owner)
        .await;
    suite
        .approve_add_genesis_miner(&operator_chain_2, meme_user_owner)
        .await;

    /*
    let QueryOutcome { response, .. } = proxy_chain
        .graphql_query(
            suite.proxy_application_id.unwrap(),
            "query { genesisMiners }",
        )
        .await;
    let expected =
        json!({"genesisMiners": [proxy_user_2, proxy_user_3, proxy_user_1, meme_user_owner]});
    assert_eq!(response, expected);
    */

    suite
        .fund_chain(
            &meme_user_chain,
            OPEN_CHAIN_FEE_BUDGET.try_add(suite.initial_native).unwrap(),
        )
        .await;
    suite.create_meme_application(&meme_user_chain, false).await;

    let QueryOutcome { response, .. } = proxy_chain
        .graphql_query(
            suite.proxy_application_id.unwrap(),
            "query { memeChainCreationMessages }",
        )
        .await;
    assert_eq!(
        response["memeChainCreationMessages"]
            .as_array()
            .unwrap()
            .len(),
        1
    );
    let message_id = MessageId::from_str(
        response["memeChainCreationMessages"].as_array().unwrap()[0]
            .as_str()
            .unwrap(),
    )
    .unwrap();

    let QueryOutcome { response, .. } = proxy_chain
        .graphql_query(
            suite.proxy_application_id.unwrap(),
            "query { memeApplicationIds }",
        )
        .await;
    let meme_application: Option<ApplicationId> =
        serde_json::from_value(response["memeApplicationIds"].as_array().unwrap()[0].clone())
            .unwrap();
    assert_eq!(meme_application.is_none(), true);

    let description = ChainDescription::Child(message_id);
    let meme_chain = ActiveChain::new(
        meme_user_key_pair.copy(),
        description,
        suite.clone().validator,
    );

    suite.validator.add_chain(meme_chain.clone());

    proxy_chain.handle_received_messages().await;
    meme_chain.handle_received_messages().await;
    proxy_chain.handle_received_messages().await;
    meme_chain.handle_received_messages().await;
    proxy_chain.handle_received_messages().await;
    meme_chain.handle_received_messages().await;

    let QueryOutcome { response, .. } = proxy_chain
        .graphql_query(
            suite.proxy_application_id.unwrap(),
            "query { memeApplicationIds }",
        )
        .await;
    let meme_application: Option<ApplicationId> =
        serde_json::from_value(response["memeApplicationIds"].as_array().unwrap()[0].clone())
            .unwrap();
    assert_eq!(meme_application.is_some(), true);

    proxy_chain.handle_received_messages().await;
    swap_chain.handle_received_messages().await;
    meme_chain.handle_received_messages().await;
    proxy_chain.handle_received_messages().await;
    swap_chain.handle_received_messages().await;
    meme_chain.handle_received_messages().await;
    proxy_chain.handle_received_messages().await;
    swap_chain.handle_received_messages().await;
    meme_chain.handle_received_messages().await;
}
