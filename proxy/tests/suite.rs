// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

//! Integration tests for the Proxy application.

#![cfg(not(target_arch = "wasm32"))]

use abi::{
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
        Account, AccountOwner, Amount, ApplicationId, ChainId, CryptoHash, ModuleId, TestString,
        TimeoutConfig,
    },
    test::{ActiveChain, Medium, MessageAction, Recipient, TestValidator},
};

#[derive(Clone)]
#[allow(dead_code)]
pub struct TestSuite {
    pub validator: TestValidator,

    pub admin_chain: ActiveChain,
    pub proxy_chain: ActiveChain,
    pub meme_user_chain: ActiveChain,
    pub meme_miner_chain: ActiveChain,
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

#[allow(dead_code)]
impl TestSuite {
    pub async fn new() -> Self {
        let (validator, proxy_bytecode_id) =
            TestValidator::with_current_module::<ProxyAbi, (), InstantiationArgument>().await;

        let admin_chain = validator.get_chain(&ChainId::root(0));
        let proxy_chain = validator.new_chain().await;
        let meme_user_chain = validator.new_chain().await;
        let meme_miner_chain = validator.new_chain().await;
        let operator_chain_1 = validator.new_chain().await;
        let operator_chain_2 = validator.new_chain().await;
        let swap_chain = validator.new_chain().await;

        let meme_bytecode_id = proxy_chain.publish_bytecode_files_in("../meme").await;

        Self {
            validator,

            admin_chain,
            proxy_chain,
            meme_user_chain,
            meme_miner_chain,
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

    pub async fn create_proxy_application(&mut self, operators: Vec<Account>) {
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

    pub async fn fund_chain(&self, chain: &ActiveChain, amount: Amount) {
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

    pub async fn create_swap_application(&mut self) {
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

    pub async fn propose_add_genesis_miner(&self, chain: &ActiveChain, owner: Account) {
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

    pub async fn approve_add_genesis_miner(&self, chain: &ActiveChain, owner: Account) {
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

    pub async fn create_meme_application(
        &self,
        chain: &ActiveChain,
        virtual_initial_liquidity: bool,
    ) {
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
                                    live_stream: None,
                                },
                                virtual_initial_liquidity,
                                initial_liquidity: None,
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

    pub async fn change_ownership(&self, chain: &ActiveChain, owners: Vec<AccountOwner>) {
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
