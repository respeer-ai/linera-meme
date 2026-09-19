// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

use abi::meme_token::MemeToken;
use abi::pool::Pool;
use linera_sdk::{
    linera_base_types::{Account, Amount, ApplicationId},
    views::{linera_views, MapView, RegisterView, RootView, ViewStorageContext},
};
use std::collections::HashMap;

/// The typed state V1 for pool.
#[derive(RootView)]
#[view(context = ViewStorageContext)]
pub struct PoolState {
    pub business_application_id: RegisterView<Option<ApplicationId>>,
    pub operator: RegisterView<Option<Account>>,

    pub pool: RegisterView<Option<Pool>>,
    pub router_application_id: RegisterView<Option<ApplicationId>>,

    pub total_supply: RegisterView<Amount>,
    pub shares: MapView<Account, Amount>,

    pub claimable_balances: MapView<MemeToken, HashMap<Account, Amount>>,
    pub claiming_balances: MapView<MemeToken, HashMap<Account, Amount>>,

    pub transaction_id: RegisterView<u32>,
}

pub mod adapter;
pub mod errors;
pub mod state_impl;
