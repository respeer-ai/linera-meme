// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

//! Integration tests for the Swap application.

#![cfg(not(target_arch = "wasm32"))]

use abi::{
    meme::{
        InstantiationArgument as MemeInstantiationArgument, Liquidity, Meme, MemeAbi,
        MemeParameters, Metadata,
    },
    store_type::StoreType,
    swap::router::{InstantiationArgument as SwapInstantiationArgument, SwapAbi},
};
use linera_sdk::{
    base::Amount,
    test::{QueryOutcome, TestValidator},
};

/// Test setting a swap and testing its coherency across microchains.
///
/// Creates the application on a `chain`, initializing it with a 42 then adds 15 and obtains 57.
/// which is then checked.
#[tokio::test(flavor = "multi_thread")]
async fn multi_chain_test() {
    let (validator, swap_bytecode_id) =
        TestValidator::with_current_bytecode::<SwapAbi, (), SwapInstantiationArgument>().await;

    let mut swap_chain = validator.new_chain().await;
    let mut meme_chain = validator.new_chain().await;

    let liquidity_rfq_bytecode_id = swap_chain.publish_bytecodes_in("../liquidity-rfq").await;

    let swap_application_id = meme_chain
        .create_application::<SwapAbi, (), SwapInstantiationArgument>(
            swap_bytecode_id,
            (),
            SwapInstantiationArgument {
                liquidity_rfq_bytecode_id,
            },
            vec![],
        )
        .await;

    let meme_bytecode_id = swap_chain.publish_bytecodes_in("../meme").await;

    let initial_supply = Amount::from_tokens(21000000);
    let initial_liquidity = Amount::from_tokens(11000000);

    let meme_instantiation_argument = MemeInstantiationArgument {
        meme: Meme {
            name: "Test Token".to_string(),
            ticker: "LTT".to_string(),
            decimals: 6,
            initial_supply,
            total_supply: initial_supply,
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
            native_amount: Amount::from_tokens(10),
        }),
        blob_gateway_application_id: None,
        ams_application_id: None,
        proxy_application_id: None,
        swap_application_id: Some(swap_application_id.forget_abi()),
        virtual_initial_liquidity: true,
    };

    let meme_application_id = meme_chain
        .create_application::<MemeAbi, MemeParameters, MemeInstantiationArgument>(
            meme_bytecode_id,
            MemeParameters {},
            meme_instantiation_argument.clone(),
            vec![],
        )
        .await;
}
