use abi::ams::Metadata;
use async_graphql::SimpleObject;
use linera_sdk::{
    linera_base_types::{Account, ApplicationId},
    views::{linera_views, MapView, QueueView, RegisterView, RootView, ViewStorageContext},
};

#[derive(RootView, SimpleObject)]
#[view(context = ViewStorageContext)]
pub struct AmsState {
    pub application_types: QueueView<String>,
    pub applications: MapView<ApplicationId, Metadata>,
    pub operator: RegisterView<Option<Account>>,
    pub subscribed_creator_chain: RegisterView<bool>,
}

pub mod adapter;
pub mod errors;
pub mod state_impl;
