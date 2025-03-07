// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

use abi::swap::pool::Pool;
use linera_sdk::views::{linera_views, RegisterView, RootView, ViewStorageContext};

/// The application state.
#[derive(RootView)]
#[view(context = "ViewStorageContext")]
pub struct PoolState {
    pub pool: RegisterView<Option<Pool>>,
}
