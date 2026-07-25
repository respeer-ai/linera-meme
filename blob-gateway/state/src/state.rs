use abi::blob_gateway::BlobData;
use linera_sdk::{
    linera_base_types::{ApplicationId, CryptoHash},
    views::{linera_views, MapView, RegisterView, RootView, ViewStorageContext},
};

#[derive(RootView)]
#[view(context = ViewStorageContext)]
pub struct BlobGatewayStateV1 {
    pub business_application_id: RegisterView<Option<ApplicationId>>,
    pub blobs: MapView<CryptoHash, BlobData>,
}

pub mod adapter;
pub mod errors;
pub mod state_impl;
