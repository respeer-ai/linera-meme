use async_graphql::SimpleObject;
use linera_sdk::{
    linera_base_types::ApplicationId,
    views::{linera_views, RegisterView, RootView, ViewStorageContext},
};

#[derive(RootView, SimpleObject)]
#[view(context = ViewStorageContext)]
pub struct AmsState {
    pub state_app_id: RegisterView<Option<ApplicationId>>,
}

pub mod adapter;
pub mod errors;
pub mod state_impl;
