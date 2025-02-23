// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

//! Integration tests for the Meme application.

#![cfg(not(target_arch = "wasm32"))]

use abi::{
    meme::{InstantiationArgument, Meme, Metadata, Mint},
    store_type::StoreType,
};
use linera_sdk::{
    base::Amount,
    test::{QueryOutcome, TestValidator},
};
use std::collections::HashMap;
use std::str::FromStr;

/// Test setting a counter and testing its coherency across microchains.
///
/// Creates the application on a `chain`, initializing it with a 42 then adds 15 and obtains 57.
/// which is then checked.
#[tokio::test(flavor = "multi_thread")]
async fn single_chain_test() {
    let (validator, bytecode_id) =
        TestValidator::with_current_bytecode::<meme::MemeAbi, (), InstantiationArgument>().await;
    let mut chain = validator.new_chain().await;

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
        mint: Some(Mint {
            fixed_currency: true,
            initial_currency: Amount::from_str("0.0000001").unwrap(),
        }),
        fee_percent: Some(Amount::from_str("0.2").unwrap()),
        blob_gateway_application_id: None,
        ams_application_id: None,
        swap_application_id: None,
        initial_balances: HashMap::new(),
    };

    let application_id = chain
        .create_application(bytecode_id, (), instantiation_argument.clone(), vec![])
        .await;

    let QueryOutcome { response, .. } = chain
        .graphql_query(application_id, "query { totalSupply }")
        .await;
    assert_eq!(
        Amount::from_str(response["totalSupply"].as_str().unwrap()).unwrap(),
        instantiation_argument.meme.total_supply
    );
}
