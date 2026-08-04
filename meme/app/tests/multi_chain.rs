// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

//! Integration tests for the Meme business application.

#![cfg(not(target_arch = "wasm32"))]

use abi::{
    meme::{
        HandoffArgument, InitializeArgument, InstantiationArgument as MemeInstantiationArgument,
        Liquidity, Meme, MemeAbi, MemeOperation, MemeParameters, Metadata,
        StateInstantiationArgument,
    },
    store_type::StoreType,
    swap::router::{InstantiationArgument as SwapInstantiationArgument, SwapAbi, SwapParameters},
};
use async_graphql::{Request, Variables};
use linera_sdk::{
    linera_base_types::{
        Account, AccountOwner, Amount, ApplicationId, ChainId, CryptoHash, ModuleId, TestString,
    },
    test::{ActiveChain, MessageAction, QueryOutcome, TestValidator},
};
use meme_test_proxy::{FakeProxyAbi, FakeProxyOperation};
use serde_json::json;
use std::str::FromStr;

#[derive(Clone)]
pub struct TestSuite {
    pub admin_chain: ActiveChain,
    pub meme_chain: ActiveChain,
    pub user_chain: ActiveChain,
    pub swap_chain: ActiveChain,

    pub swap_application_id: Option<ApplicationId>,
    pub meme_application_id: Option<ApplicationId<MemeAbi>>,
    pub state_application_id: Option<ApplicationId>,
    pub fake_proxy_application_id: Option<ApplicationId<FakeProxyAbi>>,
    pub meme_bytecode_id: ModuleId<MemeAbi, MemeParameters, MemeInstantiationArgument>,

    pub initial_supply: Amount,
    pub initial_liquidity: Amount,
}

impl TestSuite {
    pub async fn new() -> Self {
        let (validator, meme_bytecode_id) = TestValidator::with_current_module::<
            MemeAbi,
            MemeParameters,
            MemeInstantiationArgument,
        >()
        .await;

        let admin_chain = validator.get_chain(&validator.admin_chain_id());
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
            state_application_id: None,
            fake_proxy_application_id: None,
            meme_bytecode_id,

            initial_supply: Amount::from_tokens(21000000),
            initial_liquidity: Amount::from_tokens(11000000),
        }
    }

    pub fn chain_account(&self, chain: ActiveChain) -> Account {
        Account {
            chain_id: chain.id(),
            owner: AccountOwner::CHAIN,
        }
    }

    pub fn chain_owner_account(&self, chain: &ActiveChain) -> Account {
        Account {
            chain_id: chain.id(),
            owner: AccountOwner::from(chain.public_key()),
        }
    }

    pub fn application_account(&self, chain_id: ChainId, application_id: ApplicationId) -> Account {
        Account {
            chain_id,
            owner: AccountOwner::from(application_id.forget_abi()),
        }
    }

    pub async fn fund_chain(&self, chain: &ActiveChain, amount: Amount) {
        let (certificate, _) = self
            .admin_chain
            .add_block(|block| {
                block.with_native_token_transfer(
                    AccountOwner::CHAIN,
                    self.chain_account(chain.clone()),
                    amount,
                );
            })
            .await;
        chain
            .add_block(move |block| {
                block.with_messages_from_by_action(&certificate, MessageAction::Accept);
            })
            .await;
        chain.handle_received_messages().await;
    }

    pub async fn create_swap_application(&mut self) {
        let pool_bytecode_id = self.swap_chain.publish_bytecode_files_in("../../pool").await;
        let swap_bytecode_id = self.swap_chain.publish_bytecode_files_in("../../swap").await;

        self.swap_application_id = Some(
            self.swap_chain
                .create_application::<SwapAbi, SwapParameters, SwapInstantiationArgument>(
                    swap_bytecode_id,
                    SwapParameters {},
                    SwapInstantiationArgument { pool_bytecode_id },
                    vec![],
                )
                .await
                .forget_abi(),
        )
    }

    pub async fn create_fake_proxy_application(&mut self) {
        let fake_proxy_bytecode_id = self
            .meme_chain
            .publish_bytecode_files_in("../test-proxy")
            .await;

        self.fake_proxy_application_id = Some(
            self.meme_chain
                .create_application::<FakeProxyAbi, (), ()>(fake_proxy_bytecode_id, (), (), vec![])
                .await,
        );
    }

    pub async fn create_meme_application(
        &mut self,
        enable_mining: bool,
        mining_supply: Option<Amount>,
    ) {
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
            proxy_application_id: Some(self.fake_proxy_application_id.unwrap().forget_abi()),
            swap_application_id: Some(self.swap_application_id.unwrap()),
        };
        let parameters = MemeParameters {
            creator: self.chain_owner_account(&self.meme_chain),
            initial_liquidity: Some(Liquidity {
                fungible_amount: self.initial_liquidity,
                native_amount: Amount::from_tokens(10),
            }),
            virtual_initial_liquidity: true,
            swap_creator_chain_id: self.swap_chain.id(),

            enable_mining,
            mining_supply,
        };

        self.meme_application_id = Some(
            self.meme_chain
                .create_application(
                    self.meme_bytecode_id.clone(),
                    parameters.clone(),
                    instantiation_argument.clone(),
                    vec![],
                )
                .await,
        )
    }

    pub async fn create_state_application(&mut self) {
        let state_bytecode_id = self.meme_chain.publish_bytecode_files_in("../state").await;
        let operator = self.chain_owner_account(&self.meme_chain);

        self.state_application_id = Some(
            self.meme_chain
                .create_application::<
                    abi::meme::MemeStateAbi,
                    (),
                    StateInstantiationArgument,
                >(
                    state_bytecode_id,
                    (),
                    StateInstantiationArgument {
                        business_application_id: self.meme_application_id.unwrap().forget_abi(),
                        operator: Some(operator),
                        proxy_application_id: Some(self.fake_proxy_application_id.unwrap().forget_abi()),
                    },
                    vec![],
                )
                .await
                .forget_abi(),
        );
    }

    pub async fn append_state(&self) {
        self.meme_chain
            .add_block(|block| {
                block.with_operation(
                    self.meme_application_id.unwrap(),
                    MemeOperation::AppendState {
                        state_application_id: self.state_application_id.unwrap(),
                    },
                );
            })
            .await;
        self.meme_chain.handle_received_messages().await;
    }

    pub async fn initialize_meme(&self) {
        let argument = InitializeArgument {
            owner: self.chain_owner_account(&self.meme_chain),
            holder: self.application_account(
                self.meme_chain.id(),
                self.meme_application_id.unwrap().forget_abi(),
            ),
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
                initial_liquidity: Some(Liquidity {
                    fungible_amount: self.initial_liquidity,
                    native_amount: Amount::from_tokens(10),
                }),
            },
            initial_owner_balance: Amount::from_tokens(100),
            blob_gateway_application_id: None,
            ams_application_id: None,
            swap_application_id: Some(self.swap_application_id.unwrap()),
            enable_mining: false,
            mining_supply: None,
            now: Default::default(),
        };

        self.meme_chain
            .add_block(|block| {
                block.with_operation(
                    self.fake_proxy_application_id.unwrap(),
                    FakeProxyOperation::InitializeMeme {
                        meme_app_id: self.meme_application_id.unwrap().forget_abi(),
                        argument,
                    },
                );
            })
            .await;
        self.meme_chain.handle_received_messages().await;
    }

    pub async fn transfer(&self, chain: &ActiveChain, to: Account, amount: Amount) {
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

    pub async fn mint(&self, chain: &ActiveChain, to: Account, amount: Amount) {
        chain
            .add_block(|block| {
                block.with_operation(
                    self.meme_application_id.unwrap(),
                    MemeOperation::Mint { to, amount },
                );
            })
            .await;
        self.meme_chain.handle_received_messages().await;
    }

    pub async fn approve(&self, chain: &ActiveChain, spender: Account, amount: Amount) {
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

    pub async fn transfer_from(
        &self,
        chain: &ActiveChain,
        from: Account,
        to: Account,
        amount: Amount,
    ) {
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

    pub async fn balance_of(&self, owner: Account) -> Amount {
        let query = Request::new(
            r#"
            query Balance($owner: Account!) {
                balanceOf(owner: $owner)
            }
            "#,
        )
        .variables(Variables::from_json(json!({
            "owner": {
                "chain_id": owner.chain_id.to_string(),
                "owner": owner.owner.to_string(),
            }
        })));
        let QueryOutcome { response, .. } = self
            .meme_chain
            .graphql_query(self.meme_application_id.unwrap(), query)
            .await;
        Amount::from_str(response["balanceOf"].as_str().unwrap()).unwrap()
    }

    pub async fn allowance_of(&self, owner: Account, spender: Account) -> Amount {
        let query = Request::new(
            r#"
            query Allowance($owner: Account!, $spender: Account!) {
                allowanceOf(owner: $owner, spender: $spender)
            }
            "#,
        )
        .variables(Variables::from_json(json!({
            "owner": {
                "chain_id": owner.chain_id.to_string(),
                "owner": owner.owner.to_string(),
            },
            "spender": {
                "chain_id": spender.chain_id.to_string(),
                "owner": spender.owner.to_string(),
            }
        })));
        let QueryOutcome { response, .. } = self
            .meme_chain
            .graphql_query(self.meme_application_id.unwrap(), query)
            .await;
        Amount::from_str(response["allowanceOf"].as_str().unwrap()).unwrap()
    }
}

#[tokio::test(flavor = "multi_thread")]
async fn meme_work_flow_no_mining_test() {
    let _ = env_logger::builder().is_test(true).try_init();

    let mut suite = TestSuite::new().await;
    let meme_chain = suite.meme_chain.clone();
    let user_chain = suite.user_chain.clone();
    let swap_chain = suite.swap_chain.clone();

    let meme_owner_account = suite.chain_owner_account(&meme_chain);
    let user_owner_account = suite.chain_owner_account(&user_chain);

    suite.create_swap_application().await;
    suite.create_fake_proxy_application().await;
    suite.create_meme_application(false, None).await;
    suite.create_state_application().await;
    suite.append_state().await;
    suite.initialize_meme().await;

    let meme_application_account = suite.application_account(
        meme_chain.id(),
        suite.meme_application_id.unwrap().forget_abi(),
    );
    let swap_application_account = suite.application_account(
        swap_chain.id(),
        suite.swap_application_id.unwrap().forget_abi(),
    );

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

    assert_eq!(
        suite.balance_of(meme_application_account).await,
        suite
            .initial_supply
            .try_sub(suite.initial_liquidity)
            .unwrap()
            .try_sub(initial_owner_balance)
            .unwrap(),
    );
    assert_eq!(suite.balance_of(meme_owner_account).await, initial_owner_balance);
    assert_eq!(
        suite.allowance_of(meme_application_account, swap_application_account).await,
        suite.initial_liquidity,
    );

    meme_chain.handle_received_messages().await;
    swap_chain.handle_received_messages().await;

    let amount = Amount::from_tokens(1);

    suite.transfer(&meme_chain, user_owner_account, amount).await;
    assert_eq!(suite.balance_of(user_owner_account).await, amount);

    suite.approve(&meme_chain, user_owner_account, amount).await;
    assert_eq!(
        suite.balance_of(meme_owner_account).await,
        initial_owner_balance.try_sub(amount).unwrap().try_sub(amount).unwrap(),
    );
    assert_eq!(
        suite.allowance_of(meme_owner_account, user_owner_account).await,
        amount,
    );

    suite
        .transfer_from(&user_chain, meme_owner_account, user_owner_account, amount)
        .await;
    assert_eq!(
        suite.balance_of(meme_owner_account).await,
        initial_owner_balance.try_sub(amount).unwrap().try_sub(amount).unwrap(),
    );
    assert_eq!(suite.balance_of(user_owner_account).await, amount.try_mul(2).unwrap());
    assert_eq!(
        suite.allowance_of(meme_owner_account, user_owner_account).await,
        Amount::ZERO,
    );

    meme_chain.handle_received_messages().await;
    swap_chain.handle_received_messages().await;

    suite.mint(&meme_chain, user_owner_account, amount).await;
    assert_eq!(suite.balance_of(user_owner_account).await, amount.try_mul(3).unwrap());
}

#[tokio::test(flavor = "multi_thread")]
async fn meme_work_flow_enable_mining_part_supply_test() {
    let _ = env_logger::builder().is_test(true).try_init();

    let mut suite = TestSuite::new().await;
    let meme_chain = suite.meme_chain.clone();
    let user_chain = suite.user_chain.clone();
    let swap_chain = suite.swap_chain.clone();

    let meme_owner_account = suite.chain_owner_account(&meme_chain);
    let user_owner_account = suite.chain_owner_account(&user_chain);

    suite.create_swap_application().await;
    suite.create_fake_proxy_application().await;
    suite
        .create_meme_application(true, Some(Amount::from_tokens(10000000)))
        .await;
    suite.create_state_application().await;
    suite.append_state().await;
    suite.initialize_meme().await;

    let meme_application_account = suite.application_account(
        meme_chain.id(),
        suite.meme_application_id.unwrap().forget_abi(),
    );
    let swap_application_account = suite.application_account(
        swap_chain.id(),
        suite.swap_application_id.unwrap().forget_abi(),
    );

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

    assert_eq!(
        suite.balance_of(meme_application_account).await,
        suite
            .initial_supply
            .try_sub(suite.initial_liquidity)
            .unwrap()
            .try_sub(initial_owner_balance)
            .unwrap(),
    );
    assert_eq!(suite.balance_of(meme_owner_account).await, initial_owner_balance);
    assert_eq!(
        suite.allowance_of(meme_application_account, swap_application_account).await,
        suite.initial_liquidity,
    );

    meme_chain.handle_received_messages().await;
    swap_chain.handle_received_messages().await;

    let amount = Amount::from_tokens(1);

    suite.transfer(&meme_chain, user_owner_account, amount).await;
    assert_eq!(suite.balance_of(user_owner_account).await, amount);

    suite.approve(&meme_chain, user_owner_account, amount).await;
    assert_eq!(
        suite.balance_of(meme_owner_account).await,
        initial_owner_balance.try_sub(amount).unwrap().try_sub(amount).unwrap(),
    );
    assert_eq!(
        suite.allowance_of(meme_owner_account, user_owner_account).await,
        amount,
    );

    suite
        .transfer_from(&user_chain, meme_owner_account, user_owner_account, amount)
        .await;
    assert_eq!(
        suite.balance_of(meme_owner_account).await,
        initial_owner_balance.try_sub(amount).unwrap().try_sub(amount).unwrap(),
    );
    assert_eq!(
        suite.balance_of(user_owner_account).await,
        amount.try_mul(2).unwrap(),
    );
    assert_eq!(
        suite.allowance_of(meme_owner_account, user_owner_account).await,
        Amount::ZERO,
    );

    meme_chain.handle_received_messages().await;
    swap_chain.handle_received_messages().await;

    suite.mint(&meme_chain, user_owner_account, amount).await;
    assert_eq!(suite.balance_of(user_owner_account).await, amount.try_mul(3).unwrap());
}

#[tokio::test(flavor = "multi_thread")]
async fn meme_work_flow_enable_mining_full_supply_test() {
    let _ = env_logger::builder().is_test(true).try_init();

    let mut suite = TestSuite::new().await;
    let meme_chain = suite.meme_chain.clone();
    let user_chain = suite.user_chain.clone();
    let swap_chain = suite.swap_chain.clone();

    let meme_owner_account = suite.chain_owner_account(&meme_chain);
    let user_owner_account = suite.chain_owner_account(&user_chain);

    suite.create_swap_application().await;
    suite.create_fake_proxy_application().await;
    suite.create_meme_application(true, None).await;
    suite.create_state_application().await;
    suite.append_state().await;
    suite.initialize_meme().await;

    let meme_application_account = suite.application_account(
        meme_chain.id(),
        suite.meme_application_id.unwrap().forget_abi(),
    );
    let swap_application_account = suite.application_account(
        swap_chain.id(),
        suite.swap_application_id.unwrap().forget_abi(),
    );

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

    assert_eq!(
        suite.balance_of(meme_application_account).await,
        suite.initial_supply.try_sub(initial_owner_balance).unwrap(),
    );
    assert_eq!(suite.balance_of(meme_owner_account).await, initial_owner_balance);
    assert_eq!(
        suite.allowance_of(meme_application_account, swap_application_account).await,
        Amount::ZERO,
    );

    meme_chain.handle_received_messages().await;
    swap_chain.handle_received_messages().await;

    let amount = Amount::from_tokens(1);

    suite.transfer(&meme_chain, user_owner_account, amount).await;
    assert_eq!(suite.balance_of(user_owner_account).await, amount);

    suite.approve(&meme_chain, user_owner_account, amount).await;
    assert_eq!(
        suite.balance_of(meme_owner_account).await,
        initial_owner_balance.try_sub(amount).unwrap().try_sub(amount).unwrap(),
    );
    assert_eq!(
        suite.allowance_of(meme_owner_account, user_owner_account).await,
        amount,
    );

    suite
        .transfer_from(&user_chain, meme_owner_account, user_owner_account, amount)
        .await;
    assert_eq!(
        suite.balance_of(meme_owner_account).await,
        initial_owner_balance.try_sub(amount).unwrap().try_sub(amount).unwrap(),
    );
    assert_eq!(
        suite.balance_of(user_owner_account).await,
        amount.try_mul(2).unwrap(),
    );
    assert_eq!(
        suite.allowance_of(meme_owner_account, user_owner_account).await,
        Amount::ZERO,
    );

    meme_chain.handle_received_messages().await;
    swap_chain.handle_received_messages().await;

    suite.mint(&meme_chain, user_owner_account, amount).await;
    assert_eq!(suite.balance_of(user_owner_account).await, amount.try_mul(3).unwrap());
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic]
async fn transfer_insufficient_funds_test() {
    let _ = env_logger::builder().is_test(true).try_init();

    let mut suite = TestSuite::new().await;
    let meme_chain = suite.meme_chain.clone();
    let user_chain = suite.user_chain.clone();

    suite.create_swap_application().await;
    suite.create_fake_proxy_application().await;
    suite.create_meme_application(false, None).await;
    suite.create_state_application().await;
    suite.append_state().await;
    suite.initialize_meme().await;

    let user_owner_account = suite.chain_owner_account(&user_chain);
    let amount = Amount::from_tokens(101);
    suite.transfer(&meme_chain, user_owner_account, amount).await;
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic]
async fn mint_from_user() {
    let _ = env_logger::builder().is_test(true).try_init();

    let mut suite = TestSuite::new().await;
    let user_chain = suite.user_chain.clone();

    suite.create_swap_application().await;
    suite.create_fake_proxy_application().await;
    suite.create_meme_application(false, None).await;
    suite.create_state_application().await;
    suite.append_state().await;
    suite.initialize_meme().await;

    let user_owner_account = suite.chain_owner_account(&user_chain);
    let amount = Amount::from_tokens(10);
    suite.mint(&user_chain, user_owner_account, amount).await;
}

#[tokio::test(flavor = "multi_thread")]
async fn append_state_and_upgrade_handoff_test() {
    let _ = env_logger::builder().is_test(true).try_init();

    let mut suite = TestSuite::new().await;

    suite.create_swap_application().await;
    suite.create_fake_proxy_application().await;
    suite.create_meme_application(false, None).await;
    suite.create_state_application().await;
    suite.append_state().await;
    suite.initialize_meme().await;

    let owner = suite.chain_owner_account(&suite.meme_chain);
    let balance_v1 = suite.balance_of(owner).await;
    assert!(balance_v1 > Amount::ZERO);

    // Deploy a second business app (v2) using the same bytecode.
    let v2_application_id = suite
        .meme_chain
        .create_application(
            suite.meme_bytecode_id.clone(),
            MemeParameters {
                creator: owner,
                initial_liquidity: Some(Liquidity {
                    fungible_amount: suite.initial_liquidity,
                    native_amount: Amount::from_tokens(10),
                }),
                virtual_initial_liquidity: true,
                swap_creator_chain_id: suite.swap_chain.id(),
                enable_mining: false,
                mining_supply: None,
            },
            MemeInstantiationArgument {
                meme: Meme {
                    name: "Test Token".to_string(),
                    ticker: "LTT".to_string(),
                    decimals: 6,
                    initial_supply: suite.initial_supply,
                    total_supply: suite.initial_supply,
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
                proxy_application_id: Some(suite.fake_proxy_application_id.unwrap().forget_abi()),
                swap_application_id: Some(suite.swap_application_id.unwrap()),
            },
            vec![],
        )
        .await;

    // Append the existing state app to v2 as well.
    suite.meme_chain
        .add_block(|block| {
            block.with_operation(
                v2_application_id,
                MemeOperation::AppendState {
                    state_application_id: suite.state_application_id.unwrap(),
                },
            );
        })
        .await;
    suite.meme_chain.handle_received_messages().await;

    // Handoff: point the state app to the new business app id.
    suite.meme_chain
        .add_block(|block| {
            block.with_operation(
                suite.meme_application_id.unwrap(),
                MemeOperation::Handoff {
                    argument: HandoffArgument {
                        new_business_application_id: v2_application_id.forget_abi(),
                        new_proxy_application_id: None,
                        new_swap_application_id: None,
                        new_ams_application_id: None,
                        new_blob_gateway_application_id: None,
                    },
                },
            );
        })
        .await;
    suite.meme_chain.handle_received_messages().await;

    // v2 should now be able to read the same state.
    let QueryOutcome { response, .. } = suite
        .meme_chain
        .graphql_query(v2_application_id, "query { totalSupply }")
        .await;
    assert_eq!(
        Amount::from_str(response["totalSupply"].as_str().unwrap()).unwrap(),
        suite.initial_supply
    );

    let v2_balance = suite.balance_of(owner).await;
    assert_eq!(v2_balance, balance_v1);
}
