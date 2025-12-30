// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

use abi::meme::{Liquidity, Meme};
use linera_sdk::{
    linera_base_types::{Account, Amount, ApplicationId},
    views::{linera_views, MapView, RegisterView, RootView, ViewStorageContext},
};
use std::collections::HashMap;

/// The application state.
#[derive(RootView)]
#[view(context = ViewStorageContext)]
pub struct MemeState {
    pub initial_owner_balance: RegisterView<Amount>,
    pub owner: RegisterView<Option<Account>>,
    pub holder: RegisterView<Option<Account>>,

    // Meme metadata
    pub meme: RegisterView<Option<Meme>>,
    pub initial_liquidity: RegisterView<Option<Liquidity>>,

    pub blob_gateway_application_id: RegisterView<Option<ApplicationId>>,
    pub ams_application_id: RegisterView<Option<ApplicationId>>,
    pub proxy_application_id: RegisterView<Option<ApplicationId>>,
    pub swap_application_id: RegisterView<Option<ApplicationId>>,

    // Account information
    pub balances: MapView<Account, Amount>,
    pub allowances: MapView<Account, HashMap<Account, Amount>>,
}

pub mod adapter;
pub mod errors;
pub mod state_impl;
