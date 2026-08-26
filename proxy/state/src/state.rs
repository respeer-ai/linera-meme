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

/// The typed state V1 for proxy.
#[derive(RootView)]
#[view(context = ViewStorageContext)]
pub struct ProxyState {
    pub business_application_id: RegisterView<Option<ApplicationId>>,
    pub operator: RegisterView<Option<Account>>,
    pub meme_bytecode_id: RegisterView<Option<ModuleId>>,
    pub meme_state_bytecode_ids: MapView<u16, ModuleId>,
    pub operators: MapView<Account, Approval>,
    pub banning_operators: MapView<Account, Approval>,
    pub genesis_miners: MapView<Account, GenesisMiner>,
    pub removing_genesis_miners: MapView<Account, Approval>,
    pub miners: MapView<Account, Miner>,
    pub chains: MapView<ChainId, Chain>,
    pub swap_application_id: RegisterView<Option<ApplicationId>>,
}

pub mod adapter;
pub mod errors;
pub mod state_impl;
