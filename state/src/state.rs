use linera_sdk::{
    linera_base_types::{Account, ApplicationId},
    views::{linera_views, MapView, RegisterView, RootView, ViewStorageContext},
};

#[derive(RootView)]
#[view(context = ViewStorageContext)]
pub struct State {
    pub operator: RegisterView<Option<Account>>,
    pub frozen_namespaces: RegisterView<bool>,
    pub namespace_apps: MapView<u8, Vec<ApplicationId>>,
    pub records: MapView<Vec<u8>, Vec<u8>>,
}

pub mod adapter;
pub mod errors;
pub mod state_impl;
