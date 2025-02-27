// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

use abi::swap::{pool::Pool, transaction::Transaction};
use linera_sdk::{
    base::ApplicationId,
    views::{linera_views, MapView, QueueView, RegisterView, RootView, ViewStorageContext},
};
use std::collections::HashMap;

/// The application state.
#[derive(RootView)]
#[view(context = "ViewStorageContext")]
pub struct SwapState {
    pub meme_meme_pools: MapView<ApplicationId, HashMap<ApplicationId, Pool>>,
    pub meme_native_pools: MapView<ApplicationId, Pool>,
    pub pool_id: RegisterView<u64>,
    pub pool_meme_memes: MapView<u64, Vec<ApplicationId>>,
    pub pool_meme_natives: MapView<u64, ApplicationId>,
    pub last_transactions: QueueView<Transaction>,
    pub transaction_id: RegisterView<u64>,
}
