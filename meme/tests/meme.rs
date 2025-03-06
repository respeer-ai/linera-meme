// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

//! Integration tests for the Meme application.

#![cfg(not(target_arch = "wasm32"))]

use abi::{
    meme::{
        InstantiationArgument as MemeInstantiationArgument, Liquidity, Meme, MemeAbi,
        MemeOperation, MemeParameters, Metadata,
    },
    store_type::StoreType,
    swap::router::{InstantiationArgument as SwapInstantiationArgument, SwapAbi},
};
use linera_sdk::{
    base::{Account, AccountOwner, Amount, ApplicationId, BytecodeId, ChainId, Owner},
    test::{ActiveChain, Medium, MessageAction, QueryOutcome, Recipient, TestValidator},
};
use std::str::FromStr;

#[derive(Clone)]
struct TestSuite {
    pub admin_chain: ActiveChain,
    pub meme_chain: ActiveChain,
    pub user_chain: ActiveChain,
    pub swap_chain: ActiveChain,

    pub swap_application_id: Option<ApplicationId>,
    pub meme_application_id: Option<ApplicationId<MemeAbi>>,
    pub meme_bytecode_id: BytecodeId<MemeAbi, MemeParameters, MemeInstantiationArgument>,

    pub initial_supply: Amount,
    pub initial_liquidity: Amount,
}

impl TestSuite {
    async fn new() -> Self {
        let (validator, meme_bytecode_id) = TestValidator::with_current_bytecode::<
            MemeAbi,
            MemeParameters,
            MemeInstantiationArgument,
        >()
        .await;

        let admin_chain = validator.get_chain(&ChainId::root(0));
        let meme_chain = validator.new_chain().await;
        let user_chain = validator.new_chain().await;
        let swap_chain = validator.new_chain().await;

        TestSuite {
            admin_chain,
            meme_chain,
            user_chain,
            swap_chain,

            swap_application_id: None,
            meme_application_id: None,
            meme_bytecode_id,

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

    fn application_account(&self, application_id: ApplicationId) -> Account {
        Account {
            chain_id: application_id.creation.chain_id,
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
                .await
                .forget_abi(),
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
            swap_application_id: Some(self.swap_application_id.unwrap()),
        };
        let parameters = MemeParameters {
            creator: self.chain_owner_account(&self.meme_chain),
            initial_liquidity: Some(Liquidity {
                fungible_amount: self.initial_liquidity,
                native_amount: Amount::from_tokens(10),
            }),
            virtual_initial_liquidity: true,
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

    async fn transfer(&self, chain: &ActiveChain, to: Account, amount: Amount) {
        chain
            .add_block(|block| {
                block.with_operation(
                    self.meme_application_id.unwrap(),
                    MemeOperation::Transfer { to, amount },
                );
            })
            .await;
        self.meme_chain.handle_received_messages().await;
    }

    async fn approve(&self, chain: &ActiveChain, spender: Account, amount: Amount) {
        chain
            .add_block(|block| {
                block.with_operation(
                    self.meme_application_id.unwrap(),
                    MemeOperation::Approve { spender, amount },
                );
            })
            .await;
        self.meme_chain.handle_received_messages().await;
    }

    async fn transfer_from(&self, chain: &ActiveChain, from: Account, to: Account, amount: Amount) {
        chain
            .add_block(|block| {
                block.with_operation(
                    self.meme_application_id.unwrap(),
                    MemeOperation::TransferFrom { from, to, amount },
                );
            })
            .await;
        self.meme_chain.handle_received_messages().await;
    }

    async fn initialize_liquidity(&self, chain: &ActiveChain) {
        chain
            .add_block(|block| {
                block.with_operation(
                    self.meme_application_id.unwrap(),
                    MemeOperation::InitializeLiquidity,
                );
            })
            .await;
        self.meme_chain.handle_received_messages().await;
    }
}

/// Test setting a counter and testing its coherency across microchains.
///
/// Creates the application on a `chain`, initializing it with a 42 then adds 15 and obtains 57.
/// which is then checked.
#[tokio::test(flavor = "multi_thread")]
async fn meme_work_flow_test() {
    let _ = env_logger::builder().is_test(true).try_init();

    let mut suite = TestSuite::new().await;
    let meme_chain = suite.meme_chain.clone();
    let user_chain = suite.user_chain.clone();
    let swap_chain = suite.swap_chain.clone();

    let meme_owner_account = suite.chain_owner_account(&meme_chain);
    let user_owner_account = suite.chain_owner_account(&user_chain);

    let balance = Amount::from_tokens(1);
    suite.fund_chain(&meme_chain, balance).await;

    suite.create_swap_application().await;

    meme_chain
        .register_application(suite.swap_application_id.unwrap())
        .await;

    suite.create_meme_application().await;

    let meme_application_account =
        suite.application_account(suite.meme_application_id.unwrap().forget_abi());
    let swap_application_account =
        suite.application_account(suite.swap_application_id.unwrap().forget_abi());

    user_chain
        .register_application(suite.meme_application_id.unwrap())
        .await;

    let QueryOutcome { response, .. } = meme_chain
        .graphql_query(suite.meme_application_id.unwrap(), "query { totalSupply }")
        .await;
    assert_eq!(
        Amount::from_str(response["totalSupply"].as_str().unwrap()).unwrap(),
        suite.initial_supply
    );

    let QueryOutcome { response, .. } = meme_chain
        .graphql_query(
            suite.meme_application_id.unwrap(),
            "query { initialOwnerBalance }",
        )
        .await;
    let initial_owner_balance =
        Amount::from_str(response["initialOwnerBalance"].as_str().unwrap()).unwrap();

    let query = format!(
        "query {{ balanceOf(owner: \"{}\")}}",
        meme_application_account,
    );
    let QueryOutcome { response, .. } = meme_chain
        .graphql_query(suite.meme_application_id.unwrap(), query)
        .await;
    assert_eq!(
        Amount::from_str(response["balanceOf"].as_str().unwrap()).unwrap(),
        suite
            .initial_supply
            .try_sub(suite.initial_liquidity)
            .unwrap()
            .try_sub(initial_owner_balance)
            .unwrap(),
    );

    let query = format!("query {{ balanceOf(owner: \"{}\")}}", meme_owner_account,);
    let QueryOutcome { response, .. } = meme_chain
        .graphql_query(suite.meme_application_id.unwrap(), query)
        .await;
    assert_eq!(
        Amount::from_str(response["balanceOf"].as_str().unwrap()).unwrap(),
        initial_owner_balance,
    );

    let query = format!(
        "query {{ allowanceOf(owner: \"{}\", spender: \"{}\") }}",
        meme_application_account, swap_application_account,
    );
    let QueryOutcome { response, .. } = meme_chain
        .graphql_query(suite.meme_application_id.unwrap(), query)
        .await;
    assert_eq!(
        Amount::from_str(response["allowanceOf"].as_str().unwrap()).unwrap(),
        suite.initial_liquidity,
    );

    meme_chain.handle_received_messages().await;
    swap_chain.handle_received_messages().await;

    let amount = Amount::from_tokens(1);

    suite
        .transfer(&meme_chain, user_owner_account, amount)
        .await;

    let query = format!("query {{ balanceOf(owner: \"{}\")}}", user_owner_account,);
    let QueryOutcome { response, .. } = meme_chain
        .graphql_query(suite.meme_application_id.unwrap(), query)
        .await;
    assert_eq!(
        Amount::from_str(response["balanceOf"].as_str().unwrap()).unwrap(),
        amount,
    );

    suite.approve(&meme_chain, user_owner_account, amount).await;

    let query = format!("query {{ balanceOf(owner: \"{}\")}}", meme_owner_account,);
    let QueryOutcome { response, .. } = meme_chain
        .graphql_query(suite.meme_application_id.unwrap(), query)
        .await;
    assert_eq!(
        Amount::from_str(response["balanceOf"].as_str().unwrap()).unwrap(),
        initial_owner_balance
            .try_sub(amount)
            .unwrap()
            .try_sub(amount)
            .unwrap(),
    );

    let query = format!(
        "query {{ allowanceOf(owner: \"{}\", spender: \"{}\") }}",
        meme_owner_account, user_owner_account,
    );
    let QueryOutcome { response, .. } = meme_chain
        .graphql_query(suite.meme_application_id.unwrap(), query)
        .await;
    assert_eq!(
        Amount::from_str(response["allowanceOf"].as_str().unwrap()).unwrap(),
        amount,
    );

    suite
        .transfer_from(&user_chain, meme_owner_account, user_owner_account, amount)
        .await;

    let query = format!("query {{ balanceOf(owner: \"{}\")}}", meme_owner_account,);
    let QueryOutcome { response, .. } = meme_chain
        .graphql_query(suite.meme_application_id.unwrap(), query)
        .await;
    assert_eq!(
        Amount::from_str(response["balanceOf"].as_str().unwrap()).unwrap(),
        initial_owner_balance
            .try_sub(amount)
            .unwrap()
            .try_sub(amount)
            .unwrap(),
    );

    let query = format!("query {{ balanceOf(owner: \"{}\")}}", user_owner_account,);
    let QueryOutcome { response, .. } = meme_chain
        .graphql_query(suite.meme_application_id.unwrap(), query)
        .await;
    assert_eq!(
        Amount::from_str(response["balanceOf"].as_str().unwrap()).unwrap(),
        amount.try_mul(2).unwrap(),
    );

    let query = format!(
        "query {{ allowanceOf(owner: \"{}\", spender: \"{}\") }}",
        meme_owner_account, user_owner_account,
    );
    let QueryOutcome { response, .. } = meme_chain
        .graphql_query(suite.meme_application_id.unwrap(), query)
        .await;
    assert_eq!(
        Amount::from_str(response["allowanceOf"].as_str().unwrap()).unwrap(),
        Amount::ZERO,
    );

    let QueryOutcome { response, .. } = meme_chain
        .graphql_query(
            suite.meme_application_id.unwrap(),
            "query { liquidityPoolInitialized }",
        )
        .await;
    assert_eq!(
        response["liquidityPoolInitialized"].as_bool().unwrap(),
        false,
    );
    suite.initialize_liquidity(&meme_chain).await;
    let QueryOutcome { response, .. } = meme_chain
        .graphql_query(
            suite.meme_application_id.unwrap(),
            "query { liquidityPoolInitialized }",
        )
        .await;
    assert_eq!(
        response["liquidityPoolInitialized"].as_bool().unwrap(),
        true,
    );

    // TODO: create pool in swap application
    // TODO: purchase meme with user chain
    // TODO: add liquidity with user chain
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic]
async fn transfer_insufficient_funds_test() {
    let _ = env_logger::builder().is_test(true).try_init();

    let mut suite = TestSuite::new().await;
    let meme_chain = suite.meme_chain.clone();
    let user_chain = suite.user_chain.clone();

    let balance = Amount::from_tokens(1);
    suite.fund_chain(&meme_chain, balance).await;

    suite.create_swap_application().await;

    meme_chain
        .register_application(suite.swap_application_id.unwrap())
        .await;

    suite.create_meme_application().await;

    let user_owner_account = suite.chain_owner_account(&user_chain);

    let amount = Amount::from_tokens(101);
    suite
        .transfer(&meme_chain, user_owner_account, amount)
        .await;
}
