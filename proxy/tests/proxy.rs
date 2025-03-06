// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

//! Integration tests for the Proxy application.

#![cfg(not(target_arch = "wasm32"))]

use abi::{
    meme::{
        InstantiationArgument as MemeInstantiationArgument, Liquidity, Meme, MemeOperation,
        MemeParameters, Metadata,
    },
    proxy::{Chain, InstantiationArgument, ProxyAbi, ProxyOperation},
    store_type::StoreType,
    swap::router::{InstantiationArgument as SwapInstantiationArgument, SwapAbi},
};
use linera_sdk::{
    linera_base_types::{
        Account, AccountOwner, Amount, ApplicationId, ChainDescription, ChainId, MessageId,
        ModuleId, Owner,
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
    pub operator_chain: ActiveChain,
    pub swap_chain: ActiveChain,

    pub proxy_bytecode_id: ModuleId<ProxyAbi, (), InstantiationArgument>,
    pub meme_bytecode_id: ModuleId,
    pub proxy_application_id: Option<ApplicationId<ProxyAbi>>,
    pub swap_application_id: Option<ApplicationId<SwapAbi>>,
}

impl TestSuite {
    async fn new() -> Self {
        let (validator, proxy_bytecode_id) =
            TestValidator::with_current_bytecode::<ProxyAbi, (), InstantiationArgument>().await;

        let admin_chain = validator.get_chain(&ChainId::root(0));
        let proxy_chain = validator.new_chain().await;
        let meme_user_chain = validator.new_chain().await;
        let operator_chain = validator.new_chain().await;
        let swap_chain = validator.new_chain().await;

        let meme_bytecode_id = proxy_chain.publish_bytecodes_in("../meme").await;

        Self {
            validator,

            admin_chain,
            proxy_chain,
            meme_user_chain,
            operator_chain,
            swap_chain,

            proxy_bytecode_id,
            meme_bytecode_id,
            proxy_application_id: None,
            swap_application_id: None,
        }
    }

    async fn create_proxy_application(&mut self, operator: Account) {
        self.proxy_application_id = Some(
            self.proxy_chain
                .create_application(
                    self.proxy_bytecode_id,
                    (),
                    InstantiationArgument {
                        meme_bytecode_id: self.meme_bytecode_id,
                        operator,
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
        let liquidity_rfq_bytecode_id = self
            .swap_chain
            .publish_bytecodes_in("../liquidity-rfq")
            .await;
        let pool_bytecode_id = self.swap_chain.publish_bytecodes_in("../pool").await;
        let swap_bytecode_id = self.swap_chain.publish_bytecodes_in("../swap").await;

        self.swap_application_id = Some(
            self.swap_chain
                .create_application::<SwapAbi, (), SwapInstantiationArgument>(
                    swap_bytecode_id,
                    (),
                    SwapInstantiationArgument {
                        liquidity_rfq_bytecode_id,
                        pool_bytecode_id,
                    },
                    vec![],
                )
                .await,
        )
    }

    async fn propose_add_genesis_miner(&self, chain: &ActiveChain, owner: Owner) {
        let certificate = chain
            .add_block(|block| {
                block.with_operation(
                    self.proxy_application_id.unwrap(),
                    ProxyOperation::ProposeAddGenesisMiner {
                        owner,
                        endpoint: None,
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

    async fn approve_add_genesis_miner(&self, chain: &ActiveChain, owner: Owner) {
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

    async fn create_meme_application(&self, chain: &ActiveChain) {
        let certificate = chain
            .add_block(|block| {
                block.with_operation(
                    self.proxy_application_id.unwrap(),
                    ProxyOperation::CreateMeme {
                        fee_budget: Some(Amount::ZERO),
                        meme_instantiation_argument: MemeInstantiationArgument {
                            meme: Meme {
                                name: "Test Token".to_string(),
                                ticker: "LTT".to_string(),
                                decimals: 6,
                                initial_supply: Amount::from_tokens(21000000),
                                total_supply: Amount::from_tokens(21000000),
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
                            swap_application_id: Some(
                                self.swap_application_id.unwrap().forget_abi(),
                            ),
                        },
                        meme_parameters: MemeParameters {
                            creator: self.chain_owner_account(chain),
                            initial_liquidity: Some(Liquidity {
                                fungible_amount: Amount::from_tokens(10000000),
                                native_amount: Amount::from_tokens(10),
                            }),
                            virtual_initial_liquidity: true,
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

    async fn initialize_liquidity(
        &self,
        chain: &ActiveChain,
        meme_chain: &ActiveChain,
        meme_application_id: ApplicationId,
    ) {
        chain
            .add_block(|block| {
                block.with_operation(meme_application_id, MemeOperation::InitializeLiquidity);
            })
            .await;
        meme_chain.handle_received_messages().await;
        self.swap_chain.handle_received_messages().await;
        meme_chain.handle_received_messages().await;
    }
}

/// Test setting a proxy and testing its coherency across microchains.
///
/// Creates the application on a `chain`, initializing it with a 42 then adds 15 and obtains 57.
/// which is then checked.
#[tokio::test(flavor = "multi_thread")]
async fn proxy_create_meme_test() {
    let _ = env_logger::builder().is_test(true).try_init();

    let mut suite = TestSuite::new().await;

    let proxy_chain = suite.proxy_chain.clone();
    let meme_user_chain = suite.meme_user_chain.clone();
    let operator_chain = suite.operator_chain.clone();
    let swap_chain = suite.swap_chain.clone();

    let operator = Account {
        chain_id: operator_chain.id(),
        owner: Some(AccountOwner::User(Owner::from(operator_chain.public_key()))),
    };
    let owner = Owner::from(meme_user_chain.public_key());
    let meme_user_key_pair = meme_user_chain.key_pair();

    suite.create_swap_application().await;
    suite.create_proxy_application(operator).await;

    let QueryOutcome { response, .. } = proxy_chain
        .graphql_query(
            suite.proxy_application_id.unwrap(),
            "query { memeModuleId }",
        )
        .await;
    let expected = json!({"memeModuleId": suite.meme_bytecode_id});
    assert_eq!(response, expected);

    meme_user_chain
        .register_application(suite.proxy_application_id.unwrap())
        .await;
    operator_chain
        .register_application(suite.proxy_application_id.unwrap())
        .await;
    proxy_chain
        .register_application(suite.swap_application_id.unwrap())
        .await;

    suite
        .propose_add_genesis_miner(&operator_chain, owner)
        .await;
    suite
        .approve_add_genesis_miner(&operator_chain, owner)
        .await;

    let QueryOutcome { response, .. } = proxy_chain
        .graphql_query(
            suite.proxy_application_id.unwrap(),
            "query { genesisMiners }",
        )
        .await;
    let expected = json!({"genesisMiners": [owner]});
    assert_eq!(response, expected);

    suite.create_meme_application(&meme_user_chain).await;

    let QueryOutcome { response, .. } = proxy_chain
        .graphql_query(
            suite.proxy_application_id.unwrap(),
            "query { countMemeChains }",
        )
        .await;
    assert_eq!(response["countMemeChains"].as_u64().unwrap(), 1);

    let QueryOutcome { response, .. } = proxy_chain
        .graphql_query(
            suite.proxy_application_id.unwrap(),
            "query { memeChainCreationMessages }",
        )
        .await;
    let message_id = MessageId::from_str(
        response["memeChainCreationMessages"].as_array().unwrap()[0]
            .as_str()
            .unwrap(),
    )
    .unwrap();

    let QueryOutcome { response, .. } = proxy_chain
        .graphql_query(
            suite.proxy_application_id.unwrap(),
            "query { memeApplications }",
        )
        .await;
    let meme_application: Option<ApplicationId> =
        serde_json::from_value(response["memeApplications"].as_array().unwrap()[0].clone())
            .unwrap();
    assert_eq!(meme_application.is_none(), true);

    let description = ChainDescription::Child(message_id);
    let meme_chain = ActiveChain::new(
        meme_user_key_pair.copy(),
        description,
        suite.clone().validator,
    );

    suite.validator.add_chain(meme_chain);

    meme_chain.handle_received_messages().await;
    proxy_chain.handle_received_messages().await;

    let QueryOutcome { response, .. } = proxy_chain
        .graphql_query(
            suite.proxy_application_id.unwrap(),
            "query { memeApplications }",
        )
        .await;
    let meme_application: Option<ApplicationId> =
        serde_json::from_value(response["memeApplications"].as_array().unwrap()[0].clone())
            .unwrap();
    assert_eq!(meme_application.is_some(), true);

    log::info!(
        "Swap application: {}",
        suite.swap_application_id.unwrap().forget_abi()
    );
    meme_chain
        .register_application(suite.swap_application_id.unwrap())
        .await;
    meme_user_chain
        .register_application(meme_application.unwrap())
        .await;
    swap_chain.handle_received_messages().await;
    meme_chain.handle_received_messages().await;
    suite
        .initialize_liquidity(&meme_user_chain, &meme_chain, meme_application.unwrap())
        .await;
}
