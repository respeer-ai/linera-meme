// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

//! Integration tests for the Meme application.

#![cfg(not(target_arch = "wasm32"))]

use abi::{
    meme::{InstantiationArgument, Liquidity, Meme, MemeAbi, Metadata},
    store_type::StoreType,
};
use linera_sdk::{
    base::{Account, AccountOwner, Amount, ChainId, Owner},
    test::{Medium, MessageAction, QueryOutcome, Recipient, TestValidator},
};
use std::str::FromStr;

/// Test setting a counter and testing its coherency across microchains.
///
/// Creates the application on a `chain`, initializing it with a 42 then adds 15 and obtains 57.
/// which is then checked.
#[tokio::test(flavor = "multi_thread")]
async fn multi_chain_test() {
    let (validator, bytecode_id) =
        TestValidator::with_current_bytecode::<MemeAbi, (), InstantiationArgument>().await;

    let admin_chain = validator.get_chain(&ChainId::root(0));
    let mut meme_chain = validator.new_chain().await;
    let user_chain = validator.new_chain().await;

    let meme_owner = AccountOwner::User(Owner::from(meme_chain.public_key()));
    let user_owner = AccountOwner::User(Owner::from(user_chain.public_key()));

    let certificate = admin_chain
        .add_block(|block| {
            block.with_native_token_transfer(
                None,
                Recipient::Account(Account {
                    chain_id: user_chain.id(),
                    owner: Some(user_owner),
                }),
                Amount::from_tokens(10),
            );
        })
        .await;
    user_chain
        .add_block(move |block| {
            block.with_messages_from_by_medium(
                &certificate,
                &Medium::Direct,
                MessageAction::Accept,
            );
        })
        .await;

    let instantiation_argument = InstantiationArgument {
        meme: Meme {
            name: "Test Token".to_string(),
            ticker: "LTT".to_string(),
            decimals: 6,
            initial_supply: Amount::from_tokens(21000000),
            total_supply: Amount::from_tokens(21000000),
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
        initial_liquidity: Liquidity {
            fungible_amount: Amount::from_tokens(10000000),
            native_amount: Amount::from_tokens(10),
        },
        blob_gateway_application_id: None,
        ams_application_id: None,
        proxy_application_id: None,
    };

    let application_id = meme_chain
        .create_application(bytecode_id, (), instantiation_argument.clone(), vec![])
        .await;
    let application = AccountOwner::Application(application_id.forget_abi());

    user_chain.register_application(application_id).await;

    let QueryOutcome { response, .. } = meme_chain
        .graphql_query(application_id, "query { totalSupply }")
        .await;
    assert_eq!(
        Amount::from_str(response["totalSupply"].as_str().unwrap()).unwrap(),
        instantiation_argument.meme.total_supply
    );

    let query = format!("query {{ balanceOf(owner: \"{}\") }}", user_owner);
    let QueryOutcome { response, .. } = meme_chain.graphql_query(application_id, query).await;
    assert_eq!(
        Amount::from_str(response["balanceOf"].as_str().unwrap()).unwrap(),
        Amount::ZERO,
    );

    let query = format!("query {{ nativeBalanceOf(owner: \"{}\") }}", application);
    let QueryOutcome { response, .. } = meme_chain.graphql_query(application_id, query).await;
    assert_eq!(
        Amount::from_str(response["nativeBalanceOf"].as_str().unwrap()).unwrap(),
        Amount::ZERO,
    );
    // TODO: can we get native balance from chain directly here ?
}
