// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

//! Integration tests for the Proxy application.

#![cfg(not(target_arch = "wasm32"))]

use abi::policy::open_chain_fee_budget;
use linera_sdk::{
    linera_base_types::{Account, AccountOwner, AccountSecretKey, ApplicationId, Ed25519SecretKey},
    test::{ActiveChain, QueryOutcome},
};
use serde_json::json;
use std::collections::HashSet;

mod suite;
use crate::suite::TestSuite;

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
    let meme_miner_chain = &suite.meme_miner_chain.clone();
    let operator_chain_1 = &suite.operator_chain_1.clone();
    let operator_chain_2 = &suite.operator_chain_2.clone();
    let swap_chain = &suite.swap_chain.clone();

    let operator_1 = suite.chain_owner_account(operator_chain_1);
    let operator_2 = suite.chain_owner_account(operator_chain_2);
    let meme_user_key_pair = meme_user_chain.key_pair();
    let meme_miner_owner = suite.chain_owner_account(meme_miner_chain);

    let proxy_key_1 = AccountSecretKey::Ed25519(Ed25519SecretKey::generate());
    let proxy_key_2 = AccountSecretKey::Ed25519(Ed25519SecretKey::generate());
    let proxy_key_3 = AccountSecretKey::Ed25519(Ed25519SecretKey::generate());
    let proxy_user_1 = Account {
        chain_id: proxy_chain.id(),
        owner: AccountOwner::from(proxy_key_1.public()),
    };
    let proxy_user_2 = Account {
        chain_id: proxy_chain.id(),
        owner: AccountOwner::from(proxy_key_2.public()),
    };
    let proxy_user_3 = Account {
        chain_id: proxy_chain.id(),
        owner: AccountOwner::from(proxy_key_3.public()),
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
        .propose_add_genesis_miner(&operator_chain_1, meme_miner_owner)
        .await;
    suite
        .approve_add_genesis_miner(&operator_chain_2, meme_miner_owner)
        .await;
    proxy_chain.handle_received_messages().await;

    let QueryOutcome { response, .. } = proxy_chain
        .graphql_query(
            suite.proxy_application_id.unwrap(),
            "query { genesisMiners }",
        )
        .await;
    let expected = [proxy_user_1, proxy_user_2, proxy_user_3, meme_miner_owner];
    let response: Vec<Account> = response["genesisMiners"]
        .as_array()
        .unwrap()
        .into_iter()
        .map(|owner| serde_json::from_value::<Account>(owner.clone()).unwrap())
        .collect();
    assert_eq!(response.len(), 4);

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
    let description = suite.create_meme_application(&meme_user_chain, false).await;

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
