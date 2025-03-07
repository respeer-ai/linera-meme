// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

//! Integration tests for the Pool application.

#![cfg(not(target_arch = "wasm32"))]

use abi::swap::pool::{InstantiationArgument, PoolAbi, PoolParameters};
use linera_sdk::test::{QueryOutcome, TestValidator};

/// Test setting a pool and testing its coherency across microchains.
///
/// Creates the application on a `chain`, initializing it with a 42 then adds 15 and obtains 57.
/// which is then checked.
#[tokio::test(flavor = "multi_thread")]
async fn single_chain_test() {
    let (validator, bytecode_id) =
        TestValidator::with_current_module::<PoolAbi, PoolParameters, InstantiationArgument>()
            .await;
    let mut chain = validator.new_chain().await;
}
