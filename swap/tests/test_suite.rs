// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

//! Shared helpers for swap integration tests that need to create meme apps
//! through the proxy (the only supported creation path after meme/state split).

#![cfg(not(target_arch = "wasm32"))]

use abi::{
    meme::{
        InstantiationArgument as MemeInstantiationArgument, Liquidity, Meme, MemeAbi,
        MemeParameters, Metadata,
    },
    policy::open_chain_fee_budget,
    proxy::{
        state_v1::{ProxyStateAbi, StateInstantiationArgument},
        InitializeArgument, InstantiationArgument as ProxyInstantiationArgument, ProxyAbi,
        ProxyOperation, StateBytecodeId,
    },
    store_type::StoreType,
    swap::router::{InstantiationArgument as SwapInstantiationArgument, SwapAbi, SwapParameters},
};
use linera_sdk::{
    linera_base_types::{
        Account, AccountOwner, Amount, ApplicationId, BlobType, ChainDescription, CryptoHash,
        ModuleId, TestString,
    },
    test::{ActiveChain, MessageAction, QueryOutcome, TestValidator},
};
use std::collections::HashSet;

pub const DEFAULT_INITIAL_SUPPLY: Amount = Amount::from_tokens(21000000);
pub const DEFAULT_INITIAL_LIQUIDITY_FUNGIBLE: Amount = Amount::from_tokens(11000000);
pub const DEFAULT_INITIAL_LIQUIDITY_NATIVE: Amount = Amount::from_tokens(10);

/// Setup shared by swap integration tests that exercise the meme→swap path.
/// It deploys swap + proxy and exposes a helper to create meme apps via proxy.
#[derive(Clone)]
pub struct ProxyMemeSetup {
    pub validator: TestValidator,
    pub admin_chain: ActiveChain,
    pub swap_chain: ActiveChain,
    pub proxy_chain: ActiveChain,

    pub swap_application_id: ApplicationId<SwapAbi>,
    pub proxy_application_id: ApplicationId<ProxyAbi>,

    #[allow(dead_code)]
    pub meme_bytecode_id: ModuleId,
    #[allow(dead_code)]
    pub meme_state_bytecode_id: ModuleId,
}

impl ProxyMemeSetup {
    pub async fn new() -> Self {
        let (validator, swap_bytecode_id) = TestValidator::with_current_module::<
            SwapAbi,
            SwapParameters,
            SwapInstantiationArgument,
        >()
        .await;

        let admin_chain = validator.get_chain(&validator.admin_chain_id());
        let mut swap_chain = validator.new_chain().await;
        let mut proxy_chain = validator.new_chain().await;

        let pool_bytecode_id = swap_chain.publish_bytecode_files_in("../pool").await;
        let meme_bytecode_id = proxy_chain.publish_bytecode_files_in("../meme/app").await;
        let meme_state_bytecode_id = proxy_chain.publish_bytecode_files_in("../meme/state").await;
        let proxy_state_bytecode_id = proxy_chain.publish_bytecode_files_in("../proxy/state").await;

        let swap_application_id = swap_chain
            .create_application::<SwapAbi, SwapParameters, SwapInstantiationArgument>(
                swap_bytecode_id,
                SwapParameters {},
                SwapInstantiationArgument { pool_bytecode_id },
                vec![],
            )
            .await;

        let proxy_application_id = proxy_chain
            .create_application::<ProxyAbi, (), ProxyInstantiationArgument>(
                proxy_chain.publish_bytecode_files_in("../proxy/app").await,
                (),
                ProxyInstantiationArgument {},
                vec![],
            )
            .await;

        let operator = Account {
            chain_id: proxy_chain.id(),
            owner: AccountOwner::from(proxy_chain.public_key()),
        };
        let proxy_state_application_id = proxy_chain
            .create_application::<ProxyStateAbi, (), StateInstantiationArgument>(
                proxy_state_bytecode_id,
                (),
                StateInstantiationArgument {
                    business_application_id: proxy_application_id.forget_abi(),
                    operator: Some(operator),
                },
                vec![],
            )
            .await;

        proxy_chain
            .add_block(|block| {
                block.with_operation(
                    proxy_application_id,
                    ProxyOperation::AppendState {
                        state_application_id: proxy_state_application_id.forget_abi(),
                    },
                );
            })
            .await;
        proxy_chain.handle_received_messages().await;

        proxy_chain
            .add_block(|block| {
                block.with_operation(
                    proxy_application_id,
                    ProxyOperation::Initialize {
                        argument: InitializeArgument {
                            initial_operators: vec![],
                            genesis_miner_owners: vec![operator],
                            swap_application_id: swap_application_id.forget_abi(),
                            meme_bytecode_id,
                            meme_state_bytecode_ids: vec![StateBytecodeId {
                                version: 1,
                                module_id: meme_state_bytecode_id,
                            }],
                        },
                    },
                );
            })
            .await;
        proxy_chain.handle_received_messages().await;

        Self {
            validator,
            admin_chain,
            swap_chain,
            proxy_chain,
            swap_application_id,
            proxy_application_id,
            meme_bytecode_id,
            meme_state_bytecode_id,
        }
    }

    #[allow(dead_code)]
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

    #[allow(dead_code)]
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

    /// Create a meme app through the proxy and return `(meme_chain, meme_application_id)`.
    /// The meme is created on a fresh chain spawned by the proxy.
    pub async fn create_meme_application(
        &self,
        meme_user_chain: &ActiveChain,
        virtual_initial_liquidity: bool,
        enable_mining: bool,
        mining_supply: Option<Amount>,
    ) -> (ActiveChain, ApplicationId<MemeAbi>) {
        self.fund_chain(
            meme_user_chain,
            open_chain_fee_budget()
                .try_mul(2)
                .unwrap()
                .try_add(DEFAULT_INITIAL_LIQUIDITY_NATIVE)
                .unwrap(),
        )
        .await;

        let initial_liquidity = Some(Liquidity {
            fungible_amount: DEFAULT_INITIAL_LIQUIDITY_FUNGIBLE,
            native_amount: DEFAULT_INITIAL_LIQUIDITY_NATIVE,
        });

        let (certificate, _) = meme_user_chain
            .add_block(|block| {
                block.with_operation(
                    self.proxy_application_id,
                    ProxyOperation::CreateMeme {
                        meme_instantiation_argument: MemeInstantiationArgument {
                            meme: Meme {
                                name: "Test Token".to_string(),
                                ticker: "LTT".to_string(),
                                decimals: 6,
                                initial_supply: DEFAULT_INITIAL_SUPPLY,
                                total_supply: DEFAULT_INITIAL_SUPPLY,
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
                            swap_application_id: Some(self.swap_application_id.forget_abi()),
                        },
                        meme_parameters: MemeParameters {
                            creator: self.chain_owner_account(meme_user_chain),
                            initial_liquidity,
                            virtual_initial_liquidity,
                            swap_creator_chain_id: self.swap_chain.id(),
                            enable_mining,
                            mining_supply,
                        },
                    },
                );
            })
            .await;

        let previous_ids: HashSet<String> = self
            .proxy_chain
            .graphql_query(self.proxy_application_id, "query { memeApplicationIds }")
            .await
            .response["memeApplicationIds"]
            .as_array()
            .map(|arr| {
                arr.iter()
                    .filter_map(|v| v.as_str().map(String::from))
                    .collect()
            })
            .unwrap_or_default();

        let (certificate, _) = self
            .proxy_chain
            .add_block(move |block| {
                block.with_messages_from_by_action(&certificate, MessageAction::Accept);
            })
            .await;

        let block = certificate.inner().block();
        let chain_description = block
            .created_blobs()
            .into_iter()
            .filter_map(|(blob_id, blob)| {
                (blob_id.blob_type == BlobType::ChainDescription)
                    .then(|| bcs::from_bytes::<ChainDescription>(blob.content().bytes()).unwrap())
            })
            .next()
            .expect("proxy should have created a meme chain");

        let proxy_key_pair = self.proxy_chain.key_pair().copy();
        let meme_chain =
            ActiveChain::new(proxy_key_pair, chain_description, self.validator.clone());
        self.validator.add_chain(meme_chain.clone());

        for _ in 0..8 {
            self.proxy_chain.handle_received_messages().await;
            meme_chain.handle_received_messages().await;

            let QueryOutcome { response, .. } = self
                .proxy_chain
                .graphql_query(self.proxy_application_id, "query { memeApplicationIds }")
                .await;
            if let Some(arr) = response["memeApplicationIds"].as_array() {
                for value in arr {
                    if let Some(id_str) = value.as_str() {
                        if !previous_ids.contains(id_str) {
                            if let Some(id) =
                                serde_json::from_value::<Option<ApplicationId<MemeAbi>>>(
                                    value.clone(),
                                )
                                .unwrap_or(None)
                            {
                                self.proxy_chain.handle_received_messages().await;
                                meme_chain.handle_received_messages().await;
                                return (meme_chain, id);
                            }
                        }
                    }
                }
            }
        }

        panic!("meme application was not created through proxy");
    }
}
