use async_graphql::SimpleObject;
use base::types::Candidate;
use linera_sdk::{
    linera_base_types::{AccountOwner, Amount, ChainId},
    views::{linera_views, MapView, RegisterView, RootView, ViewStorageContext, QueueView},
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
