// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

//! Integration tests for the Proxy application.

#![cfg(not(target_arch = "wasm32"))]

use abi::{
    meme::{
        InstantiationArgument as MemeInstantiationArgument, Liquidity, Meme, MemeAbi,
        MemeParameters, Metadata,
    },
    policy::open_chain_fee_budget,
    proxy::{Miner, ProxyOperation},
    store_type::StoreType,
    swap::pool::PoolAbi,
};
use async_graphql::{Request, Variables};
use linera_sdk::{
    linera_base_types::{
        Account, AccountOwner, AccountSecretKey, Amount, ApplicationId, BlobType, ChainDescription,
        CryptoHash, Ed25519SecretKey, TestString,
    },
    test::{ActiveChain, QueryOutcome},
};
use pool::LiquidityAmount;
use serde_json::json;
use std::{collections::HashSet, str::FromStr};

mod suite;
use crate::suite::TestSuite;

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
    let meme_miner_chain = &suite.meme_miner_chain.clone();
    let operator_chain_1 = &suite.operator_chain_1.clone();
    let operator_chain_2 = &suite.operator_chain_2.clone();
    let swap_chain = &suite.swap_chain.clone();

    let proxy_owner = suite.chain_owner_account(proxy_chain);
    let operator_1 = suite.chain_owner_account(operator_chain_1);
    let operator_2 = suite.chain_owner_account(operator_chain_2);
    let meme_user_key_pair = meme_user_chain.key_pair();
    let swap_key_pair = swap_chain.key_pair();
    let meme_miner_owner = suite.chain_owner_account(meme_miner_chain);
    let meme_user_owner = suite.chain_owner_account(meme_user_chain);

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
        .propose_add_genesis_miner(&operator_chain_1, meme_miner_owner)
        .await;
    suite
        .approve_add_genesis_miner(&operator_chain_2, meme_miner_owner)
        .await;

    let QueryOutcome { response, .. } = proxy_chain
        .graphql_query(
            suite.proxy_application_id.unwrap(),
            "query { genesisMiners { owner registeredAt } }",
        )
        .await;

    let expected = [
        Miner {
            owner: proxy_owner,
            registered_at: 0.into(),
        },
        Miner {
            owner: meme_miner_owner,
            registered_at: 0.into(),
        },
    ];
    let response: Vec<Miner> = response["genesisMiners"]
        .as_array()
        .unwrap()
        .into_iter()
        .map(|miner| serde_json::from_value::<Miner>(miner.clone()).unwrap())
        .collect();
    assert_eq!(response.len(), 2);

    let expected: HashSet<_> = expected.iter().cloned().collect();
    let response: HashSet<_> = response.iter().cloned().collect();

    let diff: Vec<_> = expected.difference(&response).cloned().collect();
    assert_eq!(diff.len(), 0);
    let diff: Vec<_> = response.difference(&expected).cloned().collect();
    assert_eq!(diff.len(), 0);

    suite
        .fund_chain(
            &meme_user_chain,
            open_chain_fee_budget()
                .try_mul(2)
                .unwrap()
                .try_add(suite.initial_native)
                .unwrap(),
        )
        .await;
    let description = suite
        .create_meme_application(&meme_user_chain, false, false, None)
        .await;

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

    // Check meme creator balance
    let QueryOutcome { response, .. } = meme_chain
        .graphql_query(
            meme_application.unwrap().with_abi::<MemeAbi>(),
            "query { initialOwnerBalance }",
        )
        .await;
    let initial_owner_balance =
        Amount::from_str(response["initialOwnerBalance"].as_str().unwrap()).unwrap();

    let query = Request::new(
        r#"
        query Balance($owner: Account!) {
            balanceOf(owner: $owner)
        }
        "#,
    )
    .variables(Variables::from_json(json!({
        "owner": {
            "chain_id": meme_user_owner.chain_id.to_string(),
            "owner": meme_user_owner.owner.to_string(),
        }
    })));
    let QueryOutcome { response, .. } = meme_chain
        .graphql_query(meme_application.unwrap().with_abi::<MemeAbi>(), query)
        .await;
    assert_eq!(
        Amount::from_str(response["balanceOf"].as_str().unwrap()).unwrap(),
        initial_owner_balance,
    );

    proxy_chain.handle_received_messages().await;
    let certificate = swap_chain.handle_received_messages().await;
    meme_chain.handle_received_messages().await;
    proxy_chain.handle_received_messages().await;
    swap_chain.handle_received_messages().await;
    meme_chain.handle_received_messages().await;
    proxy_chain.handle_received_messages().await;
    swap_chain.handle_received_messages().await;
    meme_chain.handle_received_messages().await;

    assert!(certificate.is_some());

    let (certificate, _) = certificate.unwrap();
    let block = certificate.inner().block();
    let description = block
        .created_blobs()
        .into_iter()
        .filter_map(|(blob_id, blob)| {
            (blob_id.blob_type == BlobType::ChainDescription)
                .then(|| bcs::from_bytes::<ChainDescription>(blob.content().bytes()).unwrap())
        })
        .next()
        .unwrap();

    // Check create liquidity
    let pool_chain = ActiveChain::new(swap_key_pair.copy(), description, suite.clone().validator);

    suite.validator.add_chain(pool_chain.clone());

    pool_chain.handle_received_messages().await;
    proxy_chain.handle_received_messages().await;
    swap_chain.handle_received_messages().await;
    meme_chain.handle_received_messages().await;
    pool_chain.handle_received_messages().await;
    proxy_chain.handle_received_messages().await;
    swap_chain.handle_received_messages().await;
    meme_chain.handle_received_messages().await;
    pool_chain.handle_received_messages().await;
    proxy_chain.handle_received_messages().await;
    swap_chain.handle_received_messages().await;
    meme_chain.handle_received_messages().await;

    // Get pool application
    let QueryOutcome { response, .. } = swap_chain
        .graphql_query(
            suite.swap_application_id.unwrap(),
            "query { pools { poolApplication } }",
        )
        .await;
    assert_eq!(response["pools"].as_array().unwrap().len(), 1);
    let pool_application: Account = serde_json::from_value(
        response["pools"].as_array().unwrap()[0].clone()["poolApplication"].clone(),
    )
    .unwrap();
    let AccountOwner::Address32(application_description_hash) = pool_application.owner else {
        todo!();
    };
    let pool_application_id = ApplicationId::new(application_description_hash);
    let pool_application_id = pool_application_id.with_abi::<PoolAbi>();

    let query = Request::new(
        r#"
        query Liquidity($owner: Account!) {
            liquidity(owner: $owner) {
                liquidity
                amount0
                amount1
            }
        }
        "#,
    )
    .variables(Variables::from_json(json!({
        "owner": {
            "chain_id": meme_user_owner.chain_id.to_string(),
            "owner": meme_user_owner.owner.to_string(),
        }
    })));
    let QueryOutcome { response, .. } = pool_chain.graphql_query(pool_application_id, query).await;
    let liquidity: LiquidityAmount = serde_json::from_value(response["liquidity"].clone()).unwrap();

    assert_eq!(
        liquidity.liquidity,
        Amount::from_attos(10488088481701515469914)
    );
    assert_eq!(liquidity.amount_0, suite.initial_liquidity);
    assert_eq!(liquidity.amount_1, suite.initial_native);
}

#[tokio::test(flavor = "multi_thread")]
async fn proxy_create_meme_real_logo_blob_same_input_in_memory_test() {
    let _ = env_logger::builder().is_test(true).try_init();

    let mut suite = TestSuite::new().await;

    let proxy_chain = &suite.proxy_chain.clone();
    let meme_user_chain = &suite.meme_user_chain.clone();
    let swap_chain = &suite.swap_chain.clone();
    let operator_chain_1 = &suite.operator_chain_1.clone();
    let operator_chain_2 = &suite.operator_chain_2.clone();

    let operator_1 = suite.chain_owner_account(operator_chain_1);
    let operator_2 = suite.chain_owner_account(operator_chain_2);

    let proxy_key_1 = AccountSecretKey::Ed25519(Ed25519SecretKey::generate());
    let proxy_key_2 = AccountSecretKey::Ed25519(Ed25519SecretKey::generate());

    suite
        .change_ownership(
            proxy_chain,
            vec![proxy_key_1.public().into(), proxy_key_2.public().into()],
        )
        .await;

    suite.create_blob_gateway_application().await;
    suite.create_ams_application().await;
    suite.create_swap_application().await;
    suite
        .create_proxy_application(vec![operator_1, operator_2])
        .await;

    suite
        .fund_chain(
            &meme_user_chain,
            open_chain_fee_budget()
                .try_mul(2)
                .unwrap()
                .try_add(Amount::from_tokens(8_720))
                .unwrap(),
        )
        .await;
    let (certificate, _) = meme_user_chain
        .add_block(|block| {
            block.with_operation(
                suite.proxy_application_id.unwrap(),
                ProxyOperation::CreateMeme {
                    meme_instantiation_argument: MemeInstantiationArgument {
                        meme: Meme {
                            name: "SleepyLogoToken".to_string(),
                            ticker: "SLT".to_string(),
                            decimals: 6,
                            initial_supply: Amount::from_tokens(21_000_000),
                            total_supply: Amount::from_tokens(21_000_000),
                            metadata: Metadata {
                                logo_store_type: StoreType::Blob,
                                logo: Some(CryptoHash::new(&TestString::new(
                                    "real-logo-hash".to_string(),
                                ))),
                                description: "local submitSignedBlock helper".to_string(),
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
                        blob_gateway_application_id: Some(
                            suite.blob_gateway_application_id.unwrap().forget_abi(),
                        ),
                        ams_application_id: Some(suite.ams_application_id.unwrap().forget_abi()),
                        proxy_application_id: None,
                        swap_application_id: Some(suite.swap_application_id.unwrap().forget_abi()),
                    },
                    meme_parameters: MemeParameters {
                        creator: suite.chain_owner_account(meme_user_chain),
                        initial_liquidity: Some(Liquidity {
                            fungible_amount: Amount::from_tokens(10_499_900),
                            native_amount: Amount::from_tokens(8_720),
                        }),
                        virtual_initial_liquidity: true,
                        swap_creator_chain_id: suite.swap_chain.id(),
                        enable_mining: false,
                        mining_supply: Some(Amount::from_tokens(10_499_100)),
                    },
                },
            );
        })
        .await;
    let (certificate, _) = proxy_chain
        .add_block(move |block| {
            block.with_messages_from_by_action(
                &certificate,
                linera_sdk::test::MessageAction::Accept,
            );
        })
        .await;

    let block = certificate.inner().block();
    let description = block
        .created_blobs()
        .into_iter()
        .filter_map(|(blob_id, blob)| {
            (blob_id.blob_type == BlobType::ChainDescription)
                .then(|| bcs::from_bytes::<ChainDescription>(blob.content().bytes()).unwrap())
        })
        .next()
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
    assert_eq!(meme_application, None);

    let meme_chain = ActiveChain::new(
        proxy_chain.key_pair().copy(),
        description,
        suite.clone().validator,
    );

    suite.validator.add_chain(meme_chain.clone());

    let QueryOutcome { response, .. } = proxy_chain
        .graphql_query(
            suite.proxy_application_id.unwrap(),
            "query { memeChains { chainId token } memeApplicationIds }",
        )
        .await;
    println!("checkpoint after add_chain before child inbox: {response}");

    let certificate = meme_chain.handle_received_messages().await;
    assert!(
        certificate.is_some(),
        "meme chain should first process CreateMemeExt on the child chain"
    );

    let QueryOutcome { response, .. } = proxy_chain
        .graphql_query(
            suite.proxy_application_id.unwrap(),
            "query { memeChains { chainId token } memeApplicationIds }",
        )
        .await;
    println!("checkpoint after child CreateMemeExt: {response}");

    let certificate = proxy_chain.handle_received_messages().await;
    assert!(
        certificate.is_some(),
        "proxy should record MemeCreated after child-chain app creation"
    );
    let QueryOutcome { response, .. } = proxy_chain
        .graphql_query(
            suite.proxy_application_id.unwrap(),
            "query { memeChains { chainId token } memeApplicationIds }",
        )
        .await;
    println!("checkpoint after proxy MemeCreated: {response}");

    let certificate = meme_chain.handle_received_messages().await;
    assert!(
        certificate.is_some(),
        "meme chain should then process its self-scheduled LiquidityFunded message"
    );
    let QueryOutcome { response, .. } = proxy_chain
        .graphql_query(
            suite.proxy_application_id.unwrap(),
            "query { memeChains { chainId token } memeApplicationIds }",
        )
        .await;
    println!("checkpoint after child LiquidityFunded: {response}");

    let certificate = swap_chain.handle_received_messages().await;
    assert!(
        certificate.is_some(),
        "swap chain should process InitializeLiquidity after meme LiquidityFunded"
    );
    let QueryOutcome { response, .. } = swap_chain
        .graphql_query(
            suite.swap_application_id.unwrap(),
            "query { pools { poolApplication } }",
        )
        .await;
    println!("checkpoint after swap InitializeLiquidity: {response}");

    let (certificate, _) = certificate.unwrap();
    let block = certificate.inner().block();
    let description = block
        .created_blobs()
        .into_iter()
        .filter_map(|(blob_id, blob)| {
            (blob_id.blob_type == BlobType::ChainDescription)
                .then(|| bcs::from_bytes::<ChainDescription>(blob.content().bytes()).unwrap())
        })
        .next()
        .unwrap();

    let pool_chain = ActiveChain::new(
        swap_chain.key_pair().copy(),
        description,
        suite.clone().validator,
    );
    suite.validator.add_chain(pool_chain.clone());

    let certificate = pool_chain.handle_received_messages().await;
    assert!(
        certificate.is_some(),
        "pool chain should process CreatePool on the new child chain"
    );

    let certificate = swap_chain.handle_received_messages().await;
    assert!(
        certificate.is_some(),
        "swap chain should process PoolCreated from the pool child chain"
    );
    let QueryOutcome { response, .. } = swap_chain
        .graphql_query(
            suite.swap_application_id.unwrap(),
            "query { pools { poolApplication } }",
        )
        .await;
    println!("checkpoint after swap PoolCreated: {response}");

    let certificate = meme_chain.handle_received_messages().await;
    assert!(
        certificate.is_some(),
        "meme chain should process InitializeLiquidity callback from swap"
    );
    let QueryOutcome { response, .. } = swap_chain
        .graphql_query(
            suite.swap_application_id.unwrap(),
            "query { pools { poolApplication } }",
        )
        .await;
    println!("checkpoint after meme InitializeLiquidity callback: {response}");

    let QueryOutcome { response, .. } = proxy_chain
        .graphql_query(
            suite.proxy_application_id.unwrap(),
            "query { memeApplicationIds }",
        )
        .await;
    let meme_application: Option<ApplicationId> =
        serde_json::from_value(response["memeApplicationIds"].as_array().unwrap()[0].clone())
            .unwrap();
    assert!(meme_application.is_some());
}
