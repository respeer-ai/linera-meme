// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

use crate::{FundRequest, PoolError};
use abi::swap::{
    pool::{InstantiationArgument, Pool, PoolParameters},
    transaction::{Transaction, TransactionType},
};
use linera_sdk::{
    linera_base_types::{Account, Amount, ApplicationId, Timestamp},
    views::{linera_views, MapView, QueueView, RegisterView, RootView, ViewStorageContext},
};

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

    pub latest_transactions: QueueView<Transaction>,
    pub transaction_id: RegisterView<u32>,
}

pub mod adapter;
pub mod errors;
pub mod state_impl;
