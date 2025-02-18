// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

//! Integration tests for the Proxy application.

#![cfg(not(target_arch = "wasm32"))]

use linera_sdk::{
    base::{BytecodeId, Owner},
    test::{Medium, MessageAction, QueryOutcome, TestValidator},
};
use serde_json::json;
use std::str::FromStr;

/// Test setting a proxy and testing its coherency across microchains.
///
/// Creates the application on a `chain`, initializing it with a 42 then adds 15 and obtains 57.
/// which is then checked.
#[tokio::test(flavor = "multi_thread")]
async fn multi_chain_test() {
    let (validator, bytecode_id) =
        TestValidator::with_current_bytecode::<proxy::ProxyAbi, (), proxy::InstantiationArgument>()
            .await;

    let mut chain_1 = validator.new_chain().await;
    let chain_2 = validator.new_chain().await;
    let chain_3 = validator.new_chain().await;
    let operator = Owner::from(chain_3.public_key());

    let meme_bytecode_id = BytecodeId::from_str("58cc6e264a19cddf027010db262ca56a18e7b63e2a7ad1561ea9841f9aef308fc5ae59261c0137891a342001d3d4446a26c3666ed81aadf7e5eec6a01c86db6d").unwrap();
    let owner = Owner::from_str("02e900512d2fca22897f80a2f6932ff454f2752ef7afad18729dd25e5b5b6e00")
        .unwrap();

    let application_id = chain_1
        .create_application(
            bytecode_id,
            (),
            proxy::InstantiationArgument {
                meme_bytecode_id,
                operator,
            },
            vec![],
        )
        .await;

    let QueryOutcome { response, .. } = chain_1
        .graphql_query(application_id, "query { memeBytecodeId }")
        .await;
    let expected = json!({"memeBytecodeId": meme_bytecode_id});
    assert_eq!(response, expected);

    chain_2.register_application(application_id).await;
    chain_3.register_application(application_id).await;

    let certificate = chain_2
        .add_block(|block| {
            block.with_operation(
                application_id,
                proxy::ProxyOperation::ProposeAddGenesisMiner { owner },
            );
        })
        .await;
    chain_1
        .add_block(move |block| {
            block.with_messages_from_by_medium(
                &certificate,
                &Medium::Direct,
                MessageAction::Accept,
            );
        })
        .await;
    let certificate = chain_3
        .add_block(|block| {
            block.with_operation(
                application_id,
                proxy::ProxyOperation::ApproveAddGenesisMiner { owner },
            );
        })
        .await;
    chain_1
        .add_block(move |block| {
            block.with_messages_from_by_medium(
                &certificate,
                &Medium::Direct,
                MessageAction::Accept,
            );
        })
        .await;

    let QueryOutcome { response, .. } = chain_1
        .graphql_query(application_id, "query { genesisMiners }")
        .await;
    let expected = json!({"genesisMiners": [owner]});
    assert_eq!(response, expected);
}
