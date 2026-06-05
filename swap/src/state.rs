use abi::swap::router::Pool;
use linera_sdk::{
    linera_base_types::{ApplicationId, ChainId, ModuleId},
    views::{linera_views, MapView, RegisterView, RootView, ViewStorageContext},
};
use std::collections::HashMap;

/// The application state.
#[derive(RootView)]
#[view(context = ViewStorageContext)]
pub struct SwapState {
    pub meme_meme_pools: MapView<ApplicationId, HashMap<ApplicationId, Pool>>,
    pub meme_native_pools: MapView<ApplicationId, Pool>,

    pub pool_id: RegisterView<u64>,
    // Token pair in the two elementes vec
    pub pool_meme_memes: MapView<u64, Vec<ApplicationId>>,
    pub pool_meme_natives: MapView<u64, ApplicationId>,

    pub pool_bytecode_id: RegisterView<Option<ModuleId>>,

    pub pool_chains: MapView<ChainId, bool>,
    // We cannot invoke meme application to get meme creator chain id due to reentrant error
    // So we have to record it
    pub token_creator_chain_ids: MapView<ApplicationId, ChainId>,
}

pub mod adapter;
pub mod errors;
pub mod state_impl;
