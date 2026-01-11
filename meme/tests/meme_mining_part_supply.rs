// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

//! Integration tests for the Meme application.

#![cfg(not(target_arch = "wasm32"))]

mod test_suite;
use test_suite::TestSuite;

use abi::policy::open_chain_fee_budget;
use linera_sdk::{linera_base_types::Amount, test::QueryOutcome};
use std::str::FromStr;

#[tokio::test(flavor = "multi_thread")]
async fn meme_work_flow_enable_mining_part_supply_test() {
    let _ = env_logger::builder().is_test(true).try_init();

    let mut suite = TestSuite::new().await;
    let meme_chain = suite.meme_chain.clone();
    let user_chain = suite.user_chain.clone();
    let swap_chain = suite.swap_chain.clone();

    let meme_owner_account = suite.chain_owner_account(&meme_chain);
    let user_owner_account = suite.chain_owner_account(&user_chain);

    suite.fund_chain(&meme_chain, open_chain_fee_budget()).await;

    suite.create_swap_application().await;
    suite
        .create_meme_application(true, Some(10000000.into()))
        .await;

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

    let query = format!("query {{ balanceOf(owner: \"{}\")}}", meme_owner_account);
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

    let query = format!("query {{ balanceOf(owner: \"{}\")}}", user_owner_account);
    let QueryOutcome { response, .. } = meme_chain
        .graphql_query(suite.meme_application_id.unwrap(), query)
        .await;
    assert_eq!(
        Amount::from_str(response["balanceOf"].as_str().unwrap()).unwrap(),
        amount,
    );

    suite.approve(&meme_chain, user_owner_account, amount).await;

    let query = format!("query {{ balanceOf(owner: \"{}\")}}", meme_owner_account);
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

    let query = format!("query {{ balanceOf(owner: \"{}\")}}", meme_owner_account);
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

    let query = format!("query {{ balanceOf(owner: \"{}\")}}", user_owner_account);
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

    meme_chain.handle_received_messages().await;
    swap_chain.handle_received_messages().await;

    // TODO: create pool in swap application
    // TODO: purchase meme with user chain
    // TODO: add liquidity with user chain

    suite.mint(&meme_chain, user_owner_account, amount).await;

    let query = format!("query {{ balanceOf(owner: \"{}\")}}", user_owner_account);
    let QueryOutcome { response, .. } = meme_chain
        .graphql_query(suite.meme_application_id.unwrap(), query)
        .await;
    assert_eq!(
        Amount::from_str(response["balanceOf"].as_str().unwrap()).unwrap(),
        amount.try_mul(3).unwrap(),
    );
}
