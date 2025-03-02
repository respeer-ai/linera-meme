// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

//! Integration tests for the LiquidityRfq application.

#![cfg(not(target_arch = "wasm32"))]

use abi::swap::{
    liquidity_rfq::{LiquidityRfqAbi, LiquidityRfqOperation, LiquidityRfqParameters},
    router::{InstantiationArgument as SwapInstantiationArgument, SwapAbi},
};
use abi::{
    meme::{
        InstantiationArgument as MemeInstantiationArgument, Liquidity, Meme, MemeAbi,
        MemeParameters, Metadata,
    },
    store_type::StoreType,
};
use linera_sdk::{
    base::{Account, Amount, ChainId},
    test::{Medium, MessageAction, QueryOutcome, Recipient, TestValidator},
};

/// Test setting a liquidity rfq and testing its coherency across microchains.
///
/// Creates the application on a `chain`, initializing it with a 42 then adds 15 and obtains 57.
/// which is then checked.
#[tokio::test(flavor = "multi_thread")]
async fn multi_chain_test() {
    let (validator, rfq_bytecode_id) =
        TestValidator::with_current_bytecode::<LiquidityRfqAbi, LiquidityRfqParameters, ()>().await;

    let admin_chain = validator.get_chain(&ChainId::root(0));
    let mut swap_chain = validator.new_chain().await;
    let mut meme_chain = validator.new_chain().await;
    // Rfq chain will be created by swap chain, but we just test it here
    let mut rfq_chain = validator.new_chain().await;

    let balance = Amount::from_tokens(1278);
    let certificate = admin_chain
        .add_block(|block| {
            block.with_native_token_transfer(
                None,
                Recipient::Account(Account {
                    chain_id: meme_chain.id(),
                    owner: None,
                }),
                balance,
            );
        })
        .await;
    meme_chain
        .add_block(move |block| {
            block.with_messages_from_by_medium(
                &certificate,
                &Medium::Direct,
                MessageAction::Accept,
            );
        })
        .await;
    meme_chain.handle_received_messages().await;

    let swap_bytecode_id = swap_chain.publish_bytecodes_in("../swap").await;
    let meme_bytecode_id = swap_chain.publish_bytecodes_in("../meme").await;

    let swap_application_id = swap_chain
        .create_application::<SwapAbi, (), SwapInstantiationArgument>(
            swap_bytecode_id,
            (),
            SwapInstantiationArgument {
                liquidity_rfq_bytecode_id: rfq_bytecode_id.forget_abi(),
            },
            vec![],
        )
        .await;

    let meme_instantiation_argument = MemeInstantiationArgument {
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
        initial_liquidity: Some(Liquidity {
            fungible_amount: Amount::from_tokens(10000000),
            native_amount: Amount::from_tokens(10),
        }),
        blob_gateway_application_id: None,
        ams_application_id: None,
        proxy_application_id: None,
        swap_application_id: Some(swap_application_id.forget_abi()),
        virtual_initial_liquidity: true,
    };

    meme_chain.register_application(swap_application_id).await;
    let meme_application_id = meme_chain
        .create_application::<MemeAbi, MemeParameters, MemeInstantiationArgument>(
            meme_bytecode_id,
            MemeParameters {},
            meme_instantiation_argument,
            vec![],
        )
        .await;

    rfq_chain.register_application(swap_application_id).await;
    rfq_chain.register_application(meme_application_id).await;

    let rfq_application_id = rfq_chain
        .create_application(
            rfq_bytecode_id,
            LiquidityRfqParameters {
                token_0: meme_application_id.forget_abi(),
                token_1: None,
                amount_0: Amount::from_tokens(1),
                amount_1: None,
                router_application_id: swap_application_id.forget_abi(),
            },
            (),
            vec![],
        )
        .await;

    rfq_chain
        .add_block(|block| {
            block.with_operation(
                rfq_application_id,
                LiquidityRfqOperation::Approved {
                    token: meme_application_id.forget_abi(),
                },
            );
        })
        .await;

    let QueryOutcome { response, .. } = rfq_chain
        .graphql_query(rfq_application_id, "query { initialized }")
        .await;
    assert_eq!(
        response["initialized"].as_bool().expect("Invalid state"),
        true
    );
}
