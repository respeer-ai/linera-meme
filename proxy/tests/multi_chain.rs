// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

//! Integration tests for the Proxy application.

#![cfg(not(target_arch = "wasm32"))]

use linera_sdk::{
    base::{ApplicationId, BytecodeId, Owner},
    test::{Medium, MessageAction, QueryOutcome, TestValidator},
};
use meme::MemeAbi;
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

    let mut proxy_chain = validator.new_chain().await;
    let meme_chain = validator.new_chain().await;
    let operator_chain = validator.new_chain().await;
    let operator = Owner::from(operator_chain.public_key());

    let meme_bytecode_id = proxy_chain.publish_bytecodes_in("../meme").await;
    let owner = Owner::from(meme_chain.public_key());

    let application_id = proxy_chain
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

    let QueryOutcome { response, .. } = proxy_chain
        .graphql_query(application_id, "query { memeBytecodeId }")
        .await;
    let expected = json!({"memeBytecodeId": meme_bytecode_id});
    assert_eq!(response, expected);

    meme_chain.register_application(application_id).await;
    operator_chain.register_application(application_id).await;

    let certificate = meme_chain
        .add_block(|block| {
            block.with_operation(
                application_id,
                proxy::ProxyOperation::ProposeAddGenesisMiner {
                    owner,
                    endpoint: None,
                },
            );
        })
        .await;
    proxy_chain
        .add_block(move |block| {
            block.with_messages_from_by_medium(
                &certificate,
                &Medium::Direct,
                MessageAction::Accept,
            );
        })
        .await;
    let certificate = operator_chain
        .add_block(|block| {
            block.with_operation(
                application_id,
                proxy::ProxyOperation::ApproveAddGenesisMiner { owner },
            );
        })
        .await;
    proxy_chain
        .add_block(move |block| {
            block.with_messages_from_by_medium(
                &certificate,
                &Medium::Direct,
                MessageAction::Accept,
            );
        })
        .await;

    let QueryOutcome { response, .. } = proxy_chain
        .graphql_query(application_id, "query { genesisMiners }")
        .await;
    let expected = json!({"genesisMiners": [owner]});
    assert_eq!(response, expected);
}
