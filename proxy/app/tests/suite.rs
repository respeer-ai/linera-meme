// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

//! Integration tests for the Proxy application.

#![cfg(not(target_arch = "wasm32"))]

use abi::{
    ams::{
        AmsAbi, AmsOperation, AmsStateAbi, InstantiationArgument as AmsInstantiationArgument,
        StateInstantiationArgument as AmsStateInstantiationArgument,
    },
    blob_gateway::{
        BlobGatewayAbi, BlobGatewayOperation, BlobGatewayStateAbi,
        StateInstantiationArgument as BlobGatewayStateInstantiationArgument,
    },
    meme::{
        InstantiationArgument as MemeInstantiationArgument, Liquidity, Meme, MemeAbi,
        MemeParameters, Metadata,
    },
    proxy::{
        state_v1::{ProxyStateAbi, StateInstantiationArgument},
        InitializeArgument, InstantiationArgument, ProxyAbi, ProxyOperation, StateBytecodeId,
    },
    store_type::StoreType,
    swap::router::{InstantiationArgument as SwapInstantiationArgument, SwapAbi, SwapParameters},
};
use std::str::FromStr;

use linera_sdk::{
    linera_base_types::{
        Account, AccountOwner, Amount, ApplicationId, BlobType, ChainDescription, CryptoHash,
        ModuleId, TestString, TimeoutConfig,
    },
    test::{ActiveChain, MessageAction, QueryOutcome, TestValidator},
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
    pub meme_state_bytecode_id: ModuleId,
    pub proxy_state_bytecode_id: ModuleId<ProxyStateAbi, (), StateInstantiationArgument>,
    pub proxy_application_id: Option<ApplicationId<ProxyAbi>>,
    pub proxy_state_application_id: Option<ApplicationId<ProxyStateAbi>>,
    pub swap_application_id: Option<ApplicationId<SwapAbi>>,
    pub blob_gateway_application_id: Option<ApplicationId<BlobGatewayAbi>>,
    pub ams_application_id: Option<ApplicationId<AmsAbi>>,

    pub initial_liquidity: Amount,
    pub initial_native: Amount,
}

#[allow(dead_code)]
impl TestSuite {
    pub fn state_application_id() -> ApplicationId {
        ApplicationId::from_str("b20ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bad")
            .unwrap()
    }

    pub async fn new() -> Self {
        let (validator, proxy_bytecode_id) =
            TestValidator::with_current_module::<ProxyAbi, (), InstantiationArgument>().await;

        let admin_chain = validator.get_chain(&validator.admin_chain_id());
        let proxy_chain = validator.new_chain().await;
        let meme_user_chain = validator.new_chain().await;
        let meme_miner_chain = validator.new_chain().await;
        let operator_chain_1 = validator.new_chain().await;
        let operator_chain_2 = validator.new_chain().await;
        let swap_chain = validator.new_chain().await;

        let meme_bytecode_id = proxy_chain.publish_bytecode_files_in("../../meme/app").await;
        let meme_state_bytecode_id = proxy_chain.publish_bytecode_files_in("../../meme/state").await;
        let proxy_state_bytecode_id: ModuleId<
            ProxyStateAbi,
            (),
            StateInstantiationArgument,
        > = proxy_chain.publish_bytecode_files_in("../state").await;

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
            meme_state_bytecode_id,
            proxy_state_bytecode_id,
            proxy_application_id: None,
            proxy_state_application_id: None,
            swap_application_id: None,
            blob_gateway_application_id: None,
            ams_application_id: None,

            initial_liquidity: Amount::from_tokens(11000000),
            initial_native: Amount::from_tokens(10),
        }
    }

    pub async fn create_proxy_application(
        &mut self,
        operators: Vec<Account>,
        genesis_miner_owners: Vec<Account>,
    ) {
        let proxy_application_id = self
            .proxy_chain
            .create_application(
                self.proxy_bytecode_id,
                (),
                InstantiationArgument {},
                vec![],
            )
            .await;

        let operator = self.chain_owner_account(&self.proxy_chain);
        let proxy_state_application_id = self
            .proxy_chain
            .create_application::<ProxyStateAbi, (), StateInstantiationArgument>(
                self.proxy_state_bytecode_id,
                (),
                StateInstantiationArgument {
                    business_application_id: proxy_application_id.forget_abi(),
                    operator: Some(operator),
                },
                vec![],
            )
            .await;

        self.proxy_chain
            .add_block(|block| {
                block.with_operation(
                    proxy_application_id,
                    ProxyOperation::AppendState {
                        state_application_id: proxy_state_application_id.forget_abi(),
                    },
                );
            })
            .await;
        self.proxy_chain.handle_received_messages().await;

        self.proxy_chain
            .add_block(|block| {
                block.with_operation(
                    proxy_application_id,
                    ProxyOperation::Initialize {
                        argument: InitializeArgument {
                            initial_operators: operators.clone(),
                            genesis_miner_owners,
                            swap_application_id: self.swap_application_id.unwrap().forget_abi(),
                            meme_bytecode_id: self.meme_bytecode_id,
                            meme_state_bytecode_ids: vec![StateBytecodeId {
                                version: 1,
                                module_id: self.meme_state_bytecode_id,
                            }],
                        },
                    },
                );
            })
            .await;
        self.proxy_chain.handle_received_messages().await;

        self.proxy_application_id = Some(proxy_application_id);
        self.proxy_state_application_id = Some(proxy_state_application_id);
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
                .await,
        )
    }

    pub async fn create_blob_gateway_application(&mut self) {
        let bytecode_id = self
            .proxy_chain
            .publish_bytecode_files_in("../../blob-gateway/app")
            .await;

        let blob_gateway_application_id = self
            .proxy_chain
            .create_application::<BlobGatewayAbi, (), ()>(bytecode_id, (), (), vec![])
            .await;

        let operator = self.chain_owner_account(&self.proxy_chain);
        let state_bytecode_id = self
            .proxy_chain
            .publish_bytecode_files_in("../../blob-gateway/state")
            .await;
        let state_application_id = self
            .proxy_chain
            .create_application::<BlobGatewayStateAbi, (), BlobGatewayStateInstantiationArgument>(
                state_bytecode_id,
                (),
                BlobGatewayStateInstantiationArgument {
                    business_application_id: blob_gateway_application_id.forget_abi(),
                    operator: Some(operator),
                },
                vec![],
            )
            .await;

        self.proxy_chain
            .add_block(|block| {
                block.with_operation(
                    blob_gateway_application_id,
                    BlobGatewayOperation::AppendState {
                        state_application_id: state_application_id.forget_abi(),
                    },
                );
            })
            .await;
        self.proxy_chain.handle_received_messages().await;

        self.blob_gateway_application_id = Some(blob_gateway_application_id);
    }

    pub async fn create_ams_application(&mut self) {
        let bytecode_id = self
            .proxy_chain
            .publish_bytecode_files_in("../../ams/app")
            .await;
        let operator = self.chain_owner_account(&self.proxy_chain);

        let ams_application_id = self
            .proxy_chain
            .create_application::<AmsAbi, (), AmsInstantiationArgument>(
                bytecode_id,
                (),
                AmsInstantiationArgument {},
                vec![],
            )
            .await;

        let state_bytecode_id = self
            .proxy_chain
            .publish_bytecode_files_in("../../ams/state")
            .await;
        let state_application_id = self
            .proxy_chain
            .create_application::<AmsStateAbi, (), AmsStateInstantiationArgument>(
                state_bytecode_id,
                (),
                AmsStateInstantiationArgument {
                    business_application_id: ams_application_id.forget_abi(),
                    operator: Some(operator),
                },
                vec![],
            )
            .await;

        self.proxy_chain
            .add_block(|block| {
                block.with_operation(
                    ams_application_id,
                    AmsOperation::AppendState {
                        state_application_id: state_application_id.forget_abi(),
                    },
                );
            })
            .await;
        self.proxy_chain.handle_received_messages().await;

        self.ams_application_id = Some(ams_application_id);
    }

    pub async fn propose_add_genesis_miner(&self, chain: &ActiveChain, owner: Account) {
        let (certificate, _) = chain
            .add_block(|block| {
                block.with_operation(
                    self.proxy_application_id.unwrap(),
                    ProxyOperation::ProposeAddGenesisMiner { owner },
                );
            })
            .await;
        self.proxy_chain
            .add_block(move |block| {
                block.with_messages_from_by_action(&certificate, MessageAction::Accept);
            })
            .await;
    }

    pub async fn approve_add_genesis_miner(&self, chain: &ActiveChain, owner: Account) {
        let (certificate, _) = chain
            .add_block(|block| {
                block.with_operation(
                    self.proxy_application_id.unwrap(),
                    ProxyOperation::ApproveAddGenesisMiner { owner },
                );
            })
            .await;
        self.proxy_chain
            .add_block(move |block| {
                block.with_messages_from_by_action(&certificate, MessageAction::Accept);
            })
            .await;
    }

    pub async fn propose_remove_genesis_miner(&self, chain: &ActiveChain, owner: Account) {
        let (certificate, _) = chain
            .add_block(|block| {
                block.with_operation(
                    self.proxy_application_id.unwrap(),
                    ProxyOperation::ProposeRemoveGenesisMiner { owner },
                );
            })
            .await;
        self.proxy_chain
            .add_block(move |block| {
                block.with_messages_from_by_action(&certificate, MessageAction::Accept);
            })
            .await;
    }

    pub async fn approve_remove_genesis_miner(&self, chain: &ActiveChain, owner: Account) {
        let (certificate, _) = chain
            .add_block(|block| {
                block.with_operation(
                    self.proxy_application_id.unwrap(),
                    ProxyOperation::ApproveRemoveGenesisMiner { owner },
                );
            })
            .await;
        self.proxy_chain
            .add_block(move |block| {
                block.with_messages_from_by_action(&certificate, MessageAction::Accept);
            })
            .await;
    }

    pub async fn create_meme_application(
        &self,
        chain: &ActiveChain,
        virtual_initial_liquidity: bool,
        enable_mining: bool,
        mining_supply: Option<Amount>,
    ) -> ChainDescription {
        self.create_meme_application_with_liquidity(
            chain,
            "Test Token",
            "LTT",
            Some(Liquidity {
                fungible_amount: self.initial_liquidity,
                native_amount: self.initial_native,
            }),
            virtual_initial_liquidity,
            enable_mining,
            mining_supply,
        )
        .await
    }

    pub async fn create_meme_application_with_id(
        &self,
        chain: &ActiveChain,
        virtual_initial_liquidity: bool,
        enable_mining: bool,
        mining_supply: Option<Amount>,
    ) -> (ActiveChain, ApplicationId<MemeAbi>) {
        self.create_meme_application_with_liquidity_and_id(
            chain,
            "Test Token",
            "LTT",
            Some(Liquidity {
                fungible_amount: self.initial_liquidity,
                native_amount: self.initial_native,
            }),
            virtual_initial_liquidity,
            enable_mining,
            mining_supply,
        )
        .await
    }

    pub async fn create_meme_application_with_liquidity_and_id(
        &self,
        chain: &ActiveChain,
        name: &str,
        ticker: &str,
        initial_liquidity: Option<Liquidity>,
        virtual_initial_liquidity: bool,
        enable_mining: bool,
        mining_supply: Option<Amount>,
    ) -> (ActiveChain, ApplicationId<MemeAbi>) {
        let description = self
            .create_meme_application_with_liquidity(
                chain,
                name,
                ticker,
                initial_liquidity,
                virtual_initial_liquidity,
                enable_mining,
                mining_supply,
            )
            .await;

        let proxy_key_pair = self.proxy_chain.key_pair().copy();
        let meme_chain = ActiveChain::new(proxy_key_pair, description, self.validator.clone());
        self.validator.add_chain(meme_chain.clone());

        let previous_last_value: Option<serde_json::Value> = self
            .proxy_chain
            .graphql_query(
                self.proxy_application_id.unwrap(),
                "query { memeApplicationIds }",
            )
            .await
            .response["memeApplicationIds"]
            .as_array()
            .and_then(|arr| arr.last())
            .cloned();

        for _ in 0..8 {
            self.proxy_chain.handle_received_messages().await;
            meme_chain.handle_received_messages().await;

            let QueryOutcome { response, .. } = self
                .proxy_chain
                .graphql_query(
                    self.proxy_application_id.unwrap(),
                    "query { memeApplicationIds }",
                )
                .await;
            if let Some(value) = response["memeApplicationIds"]
                .as_array()
                .and_then(|arr| arr.last())
                .cloned()
            {
                if Some(&value) != previous_last_value.as_ref() {
                    if let Some(id) =
                        serde_json::from_value::<Option<ApplicationId<MemeAbi>>>(value)
                            .unwrap_or(None)
                    {
                        return (meme_chain, id);
                    }
                }
            }
        }

        panic!("meme application id was not registered in proxy");
    }

    pub async fn create_meme_application_with_liquidity(
        &self,
        chain: &ActiveChain,
        name: &str,
        ticker: &str,
        initial_liquidity: Option<Liquidity>,
        virtual_initial_liquidity: bool,
        enable_mining: bool,
        mining_supply: Option<Amount>,
    ) -> ChainDescription {
        let (certificate, _) = chain
            .add_block(|block| {
                block.with_operation(
                    self.proxy_application_id.unwrap(),
                    ProxyOperation::CreateMeme {
                        meme_instantiation_argument: MemeInstantiationArgument {
                            meme: Meme {
                                name: name.to_string(),
                                ticker: ticker.to_string(),
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
        let (certificate, _) = self
            .proxy_chain
            .add_block(move |block| {
                block.with_messages_from_by_action(&certificate, MessageAction::Accept);
            })
            .await;

        let block = certificate.inner().block();
        block
            .created_blobs()
            .into_iter()
            .filter_map(|(blob_id, blob)| {
                (blob_id.blob_type == BlobType::ChainDescription)
                    .then(|| bcs::from_bytes::<ChainDescription>(blob.content().bytes()).unwrap())
            })
            .next()
            .unwrap()
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
