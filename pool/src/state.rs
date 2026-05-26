// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

use crate::FundRequest;
use abi::meme_token::MemeToken;
use abi::swap::pool::Pool;
use linera_sdk::{
    linera_base_types::{Account, Amount, ApplicationId},
    views::{linera_views, MapView, RegisterView, RootView, ViewStorageContext},
};
use std::collections::HashMap;

/// The application state.
#[derive(RootView)]
#[view(context = ViewStorageContext)]
pub struct PoolState {
    pub pool: RegisterView<Option<Pool>>,
    pub router_application_id: RegisterView<Option<ApplicationId>>,

    pub transfer_id: RegisterView<u64>,
    pub fund_requests: MapView<u64, FundRequest>,

    pub total_supply: RegisterView<Amount>,
    pub shares: MapView<Account, Amount>,

    pub claim_balances: MapView<MemeToken, HashMap<Account, Amount>>,
    pub claiming_balances: MapView<MemeToken, HashMap<Account, Amount>>,

    pub transaction_id: RegisterView<u32>,
}

pub mod adapter;
pub mod errors;
pub mod state_impl;
