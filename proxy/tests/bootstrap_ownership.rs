// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

#![cfg(not(target_arch = "wasm32"))]

use abi::{
    ams::{AmsOperation, Metadata, MEME},
    blob_gateway::{BlobDataType, BlobGatewayOperation},
    policy::open_chain_fee_budget,
    store_type::StoreType,
    swap::router::SwapOperation,
};
use linera_sdk::{
    linera_base_types::{
        AccountSecretKey, Amount, CryptoHash, Ed25519SecretKey, ModuleId, TestString,
    },
    test::QueryOutcome,
};

mod suite;
use crate::suite::TestSuite;

#[tokio::test(flavor = "multi_thread")]
async fn bootstrap_multi_owner_single_leader_apps_process_frontend_protocol_operations_test() {
    let _ = env_logger::builder().is_test(true).try_init();

    let suite = TestSuite::new().await;

    let mut blob_gateway_chain = suite.proxy_chain.clone();
    let mut ams_chain = suite.operator_chain_1.clone();
    let mut swap_chain = suite.swap_chain.clone();
    let mut proxy_chain = suite.operator_chain_2.clone();
    let mut meme_user_chain = suite.meme_user_chain.clone();

    let blob_owner_0 = AccountSecretKey::Ed25519(Ed25519SecretKey::generate());
    let blob_owner_1 = AccountSecretKey::Ed25519(Ed25519SecretKey::generate());
    let ams_owner_0 = AccountSecretKey::Ed25519(Ed25519SecretKey::generate());
    let ams_owner_1 = AccountSecretKey::Ed25519(Ed25519SecretKey::generate());
    let swap_owner_0 = AccountSecretKey::Ed25519(Ed25519SecretKey::generate());
    let swap_owner_1 = AccountSecretKey::Ed25519(Ed25519SecretKey::generate());
    let proxy_owner_0 = AccountSecretKey::Ed25519(Ed25519SecretKey::generate());
    let proxy_owner_1 = AccountSecretKey::Ed25519(Ed25519SecretKey::generate());

    suite
        .change_ownership(
            &blob_gateway_chain,
            vec![blob_owner_0.public().into(), blob_owner_1.public().into()],
        )
        .await;
    suite
        .change_ownership(
            &ams_chain,
            vec![ams_owner_0.public().into(), ams_owner_1.public().into()],
        )
        .await;
    suite
        .change_ownership(
            &swap_chain,
            vec![swap_owner_0.public().into(), swap_owner_1.public().into()],
        )
        .await;
    suite
        .change_ownership(
            &proxy_chain,
            vec![proxy_owner_0.public().into(), proxy_owner_1.public().into()],
        )
        .await;

    let blob_bytecode_id = blob_gateway_chain
        .publish_bytecode_files_in("../blob-gateway")
        .await;
    let blob_gateway_application_id = blob_gateway_chain
        .create_application::<abi::blob_gateway::BlobGatewayAbi, (), ()>(
            blob_bytecode_id,
            (),
            (),
            vec![],
        )
        .await;

    let ams_bytecode_id = ams_chain.publish_bytecode_files_in("../ams/app").await;
    let ams_application_id = ams_chain
        .create_application::<abi::ams::AmsAbi, (), abi::ams::InstantiationArgument>(
            ams_bytecode_id,
            (),
            abi::ams::InstantiationArgument {
                state_app_id: TestSuite::state_application_id(),
            },
            vec![],
        )
        .await;

    let pool_bytecode_id = swap_chain.publish_bytecode_files_in("../pool").await;
    let swap_bytecode_id = swap_chain.publish_bytecode_files_in("../swap").await;
    let swap_application_id = swap_chain
        .create_application::<abi::swap::router::SwapAbi, abi::swap::router::SwapParameters, abi::swap::router::InstantiationArgument>(
            swap_bytecode_id,
            abi::swap::router::SwapParameters {},
            abi::swap::router::InstantiationArgument { pool_bytecode_id },
            vec![],
        )
        .await;

    let meme_bytecode_id: ModuleId<
        abi::meme::MemeAbi,
        abi::meme::MemeParameters,
        abi::meme::InstantiationArgument,
    > = proxy_chain.publish_bytecode_files_in("../meme").await;
    let proxy_bytecode_id = proxy_chain.publish_bytecode_files_in("../proxy").await;
    let proxy_application_id = proxy_chain
        .create_application::<abi::proxy::ProxyAbi, (), abi::proxy::InstantiationArgument>(
            proxy_bytecode_id,
            (),
            abi::proxy::InstantiationArgument {
                meme_bytecode_id: meme_bytecode_id.forget_abi(),
                operators: vec![],
                swap_application_id: swap_application_id.forget_abi(),
            },
            vec![],
        )
        .await;

    let blob_hash = CryptoHash::new(&TestString::new("bootstrap blob".to_string()));
    blob_gateway_chain
        .add_block(|block| {
            block.with_operation(
                blob_gateway_application_id,
                BlobGatewayOperation::Register {
                    store_type: StoreType::Blob,
                    data_type: BlobDataType::Image,
                    blob_hash,
                },
            );
        })
        .await;
    blob_gateway_chain.handle_received_messages().await;
    let QueryOutcome { response, .. } = blob_gateway_chain
        .graphql_query(blob_gateway_application_id, "query { blobs { blobHash } }")
        .await;
    assert_eq!(response["blobs"].as_array().unwrap().len(), 1);

    let metadata = Metadata {
        creator: suite.chain_owner_account(&ams_chain),
        application_name: "Bootstrap Meme".to_string(),
        application_id: proxy_application_id.forget_abi(),
        application_type: MEME.to_string(),
        key_words: vec!["bootstrap".to_string()],
        logo_store_type: StoreType::Blob,
        logo: blob_hash,
        description: "bootstrap ownership app operation".to_string(),
        twitter: None,
        telegram: None,
        discord: None,
        website: None,
        github: None,
        spec: None,
        created_at: 0.into(),
    };
    ams_chain
        .add_block(|block| {
            block.with_operation(ams_application_id, AmsOperation::Register { metadata });
        })
        .await;
    ams_chain.handle_received_messages().await;
    let QueryOutcome { response, .. } = ams_chain
        .graphql_query(ams_application_id, "query { applications(limit: 10) }")
        .await;
    assert_eq!(response["applications"].as_array().unwrap().len(), 1);

    let meme_bytecode_id = meme_user_chain.publish_bytecode_files_in("../meme").await;
    let meme_application_id = meme_user_chain
        .create_application::<abi::meme::MemeAbi, abi::meme::MemeParameters, abi::meme::InstantiationArgument>(
            meme_bytecode_id,
            abi::meme::MemeParameters {
                creator: suite.chain_owner_account(&meme_user_chain),
                initial_liquidity: None,
                virtual_initial_liquidity: true,
                swap_creator_chain_id: swap_chain.id(),
                enable_mining: false,
                mining_supply: None,
            },
            abi::meme::InstantiationArgument {
                meme: abi::meme::Meme {
                    name: "Bootstrap Token".to_string(),
                    ticker: "BTT".to_string(),
                    decimals: 6,
                    initial_supply: Amount::from_tokens(21_000_000),
                    total_supply: Amount::from_tokens(21_000_000),
                    metadata: abi::meme::Metadata {
                        logo_store_type: StoreType::S3,
                        logo: Some(blob_hash),
                        description: "bootstrap swap create pool".to_string(),
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
                proxy_application_id: Some(proxy_application_id.forget_abi()),
                swap_application_id: Some(swap_application_id.forget_abi()),
            },
            vec![],
        )
        .await;

    suite
        .fund_chain(
            &meme_user_chain,
            open_chain_fee_budget()
                .try_mul(2)
                .unwrap()
                .try_add(Amount::from_tokens(1))
                .unwrap(),
        )
        .await;
    meme_user_chain
        .add_block(|block| {
            block.with_operation(
                swap_application_id,
                SwapOperation::CreatePool {
                    token_0: meme_application_id.forget_abi(),
                    token_1: None,
                    amount_0: Amount::ONE,
                    amount_1: Amount::ONE,
                    to: None,
                },
            );
        })
        .await;
    let pool_creation = swap_chain.handle_received_messages().await;
    assert!(
        pool_creation.is_some(),
        "swap app must process CreatePool after bootstrap ownership change"
    );
}
