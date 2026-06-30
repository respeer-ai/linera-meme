use abi::ams::abi::Metadata;
use linera_sdk::{
    linera_base_types::{Account, ApplicationId},
    views::{linera_views, MapView, RegisterView, RootView, ViewStorageContext},
};

#[derive(RootView)]
#[view(context = ViewStorageContext)]
pub struct AmsState {
    pub business_application_id: RegisterView<Option<ApplicationId>>,
    pub operator: RegisterView<Option<Account>>,
    pub application_types: RegisterView<Vec<String>>,
    pub applications: MapView<ApplicationId, Metadata>,
}

pub mod adapter;
pub mod errors;
pub mod state_impl;
