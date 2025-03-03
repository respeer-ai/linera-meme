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
    base::{Account, AccountOwner, Amount, ChainDescription, ChainId, MessageId, Owner},
    test::{ActiveChain, Medium, MessageAction, QueryOutcome, Recipient, TestValidator},
};
use std::str::FromStr;

/// Test setting a liquidity rfq and testing its coherency across microchains.
///
/// Creates the application on a `chain`, initializing it with a 42 then adds 15 and obtains 57.
/// which is then checked.
#[tokio::test(flavor = "multi_thread")]
async fn virtual_liquidity_test() {
    let _ = env_logger::builder().is_test(true).try_init();

    let (validator, rfq_bytecode_id) =
        TestValidator::with_current_bytecode::<LiquidityRfqAbi, LiquidityRfqParameters, ()>().await;

    let admin_chain = validator.get_chain(&ChainId::root(0));
    let swap_chain = validator.new_chain().await;
    let mut meme_chain = validator.new_chain().await;
    // Rfq chain will be created by swap chain, but we just test it here
    let mut rfq_chain = validator.new_chain().await;

    let rfq_owner = AccountOwner::User(Owner::from(rfq_chain.public_key()));
    let meme_owner = AccountOwner::User(Owner::from(meme_chain.public_key()));
    let _swap_chain = swap_chain.clone();
    let swap_key_pair = _swap_chain.key_pair();
    let mut swap_chain = swap_chain;

    let balance = Amount::from_tokens(1);

    // Fund rfq chain for fee budget to create rfq chain in meme application
    let certificate = admin_chain
        .add_block(|block| {
            block.with_native_token_transfer(
                None,
                Recipient::Account(Account {
                    chain_id: rfq_chain.id(),
                    owner: None,
                }),
                balance,
            );
        })
        .await;
    rfq_chain
        .add_block(move |block| {
            block.with_messages_from_by_medium(
                &certificate,
                &Medium::Direct,
                MessageAction::Accept,
            );
        })
        .await;
    rfq_chain.handle_received_messages().await;

    // Fund meme chain for fee budget to create rfq chain in meme application
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

    let initial_liquidity = Amount::from_tokens(1100000);
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
            fungible_amount: initial_liquidity,
            native_amount: Amount::from_tokens(12),
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

    // Check meme allowance
    swap_chain.handle_received_messages().await;
    meme_chain.handle_received_messages().await;

    let QueryOutcome { response, .. } = swap_chain
        .graphql_query(swap_application_id, "query { rfqChainCreationMessages }")
        .await;
    assert_eq!(
        response["rfqChainCreationMessages"]
            .as_array()
            .unwrap()
            .len(),
        1
    );

    let creation_message_id = MessageId::from_str(
        response["rfqChainCreationMessages"].as_array().unwrap()[0]
            .as_str()
            .unwrap(),
    )
    .unwrap();
    let description = ChainDescription::Child(creation_message_id);
    let temp_chain = ActiveChain::new(swap_key_pair.copy(), description, validator);
    temp_chain.handle_received_messages().await;

    swap_chain.handle_received_messages().await;
    meme_chain.handle_received_messages().await;

    let query = format!(
        "query {{ allowanceOf(owner: \"{}\", spender: \"{}\") }}",
        AccountOwner::Application(meme_application_id.forget_abi()),
        AccountOwner::Application(swap_application_id.forget_abi()),
    );
    let QueryOutcome { response, .. } = meme_chain.graphql_query(meme_application_id, query).await;
    assert_eq!(
        Amount::from_str(response["allowanceOf"].as_str().unwrap()).unwrap(),
        initial_liquidity,
    );

    rfq_chain.register_application(swap_application_id).await;
    rfq_chain.register_application(meme_application_id).await;

    let initial_liquidity = Amount::from_tokens(1);
    let rfq_application_id = rfq_chain
        .create_application(
            rfq_bytecode_id,
            LiquidityRfqParameters {
                token_0: meme_application_id.forget_abi(),
                token_1: None,
                amount_0: initial_liquidity,
                amount_1: None,
                router_application_id: swap_application_id.forget_abi(),
            },
            (),
            vec![],
        )
        .await;

    // Check meme allowance
    meme_chain.handle_received_messages().await;

    let query = format!(
        "query {{ allowanceOf(owner: \"{}\", spender: \"{}\") }}",
        rfq_owner,
        AccountOwner::Application(swap_application_id.forget_abi()),
    );
    let QueryOutcome { response, .. } = meme_chain.graphql_query(meme_application_id, query).await;
    assert_eq!(
        Amount::from_str(response["allowanceOf"].as_str().unwrap()).unwrap(),
        initial_liquidity,
    );

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
    rfq_chain
        .add_block(|block| {
            block.with_operation(
                rfq_application_id,
                LiquidityRfqOperation::Rejected {
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
