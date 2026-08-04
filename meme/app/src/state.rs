use linera_sdk::{
    linera_base_types::ApplicationId,
    views::{linera_views, MapView, RegisterView, RootView, ViewStorageContext},
};

pub const EXPECTED_LATEST_STATE_VERSION: u16 = 1;

/// The meme business application state.
///
/// Only keeps the state application routing and versioning data.
/// All business state (balances, allowances, metadata, app ids, etc.)
/// lives in the attached state app(s).
#[derive(RootView)]
#[view(context = ViewStorageContext)]
pub struct MemeState {
    pub state_applications: MapView<u16, ApplicationId>,
    pub latest_state_version: RegisterView<u16>,
}

pub mod adapter;
pub mod errors;
pub mod state_impl;
