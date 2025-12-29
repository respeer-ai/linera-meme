// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

use abi::{
    approval::Approval,
    proxy::{Chain, GenesisMiner, Miner},
};
use linera_sdk::{
    linera_base_types::{Account, ApplicationId, ChainId, ModuleId},
    views::{linera_views, MapView, RegisterView, RootView, ViewStorageContext},
};

/// The application state.
#[derive(RootView)]
#[view(context = ViewStorageContext)]
pub struct ProxyState {
    pub meme_bytecode_id: RegisterView<Option<ModuleId>>,
    /// Active operators
    pub operators: MapView<Account, Approval>,
    /// Banning operators waiting for approval
    pub banning_operators: MapView<Account, Approval>,
    /// Genesis miner and approvals it should get
    pub genesis_miners: MapView<Account, GenesisMiner>,
    /// Removing candidates of genesis miner
    pub removing_genesis_miners: MapView<Account, Approval>,
    /// Miners and mining chains (ignore permissionless chain)
    pub miners: MapView<Account, Miner>,
    /// Chains aleady created
    pub chains: MapView<ChainId, Chain>,
    /// Swap application id for liquidity initialization
    pub swap_application_id: RegisterView<Option<ApplicationId>>,
}

pub mod adapter;
pub mod errors;
pub mod state_impl;
