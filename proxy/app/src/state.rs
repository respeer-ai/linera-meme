// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

use linera_sdk::{
    linera_base_types::ApplicationId,
    views::{linera_views, MapView, RegisterView, RootView, ViewStorageContext},
};

pub const EXPECTED_LATEST_STATE_VERSION: u16 = 1;

/// The application state.
#[derive(RootView)]
#[view(context = ViewStorageContext)]
pub struct ProxyState {
    pub state_applications: MapView<u16, ApplicationId>,
    pub latest_state_version: RegisterView<u16>,
}

pub mod adapter;
pub mod errors;
pub mod state_impl;
