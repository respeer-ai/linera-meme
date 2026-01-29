// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

//! Integration tests for the Proxy application.

#![cfg(not(target_arch = "wasm32"))]

use abi::{meme::MemeAbi, policy::open_chain_fee_budget, proxy::Miner, swap::pool::PoolAbi};
use linera_sdk::{
    linera_base_types::{Account, AccountOwner, Amount, ApplicationId, BlobType, ChainDescription},
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

    let query = format!("query {{ balanceOf(owner: \"{}\")}}", meme_user_owner);
    let QueryOutcome { response, .. } = meme_chain
        .graphql_query(meme_application.unwrap().with_abi::<MemeAbi>(), query)
        .await;
    assert_eq!(
        Amount::from_str(response["balanceOf"].as_str().unwrap()).unwrap(),
        initial_owner_balance,
    );

    proxy_chain.handle_received_messages().await;
    let certificate = swap_chain.handle_received_messages_ext().await;
    meme_chain.handle_received_messages().await;
    proxy_chain.handle_received_messages().await;
    swap_chain.handle_received_messages().await;
    meme_chain.handle_received_messages().await;
    proxy_chain.handle_received_messages().await;
    swap_chain.handle_received_messages().await;
    meme_chain.handle_received_messages().await;

    assert!(certificate.is_some());

    let certificate = certificate.unwrap();
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

    let query = format!(
        "query {{ liquidity(owner:\"{}\") {{ liquidity amount0 amount1 }} }}",
        meme_user_owner
    );
    let QueryOutcome { response, .. } = pool_chain.graphql_query(pool_application_id, query).await;
    let liquidity: LiquidityAmount = serde_json::from_value(response["liquidity"].clone()).unwrap();

    assert_eq!(
        liquidity.liquidity,
        Amount::from_attos(10488088481701515469914)
    );
    assert_eq!(liquidity.amount_0, suite.initial_liquidity);
    assert_eq!(liquidity.amount_1, suite.initial_native);
}
