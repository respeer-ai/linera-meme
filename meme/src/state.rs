// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

use linera_sdk::views::{linera_views, RegisterView, RootView, ViewStorageContext};
use abi::meme::InstantiationArgument;

/// The application state.
#[derive(RootView)]
#[view(context = "ViewStorageContext")]
pub struct MemeState {
    pub value: RegisterView<u64>,
}

#[allow(dead_code)]
impl MemeState {
    pub(crate) async fn instantiate(&mut self, argument: InstantiationArgument) {

    }
}
