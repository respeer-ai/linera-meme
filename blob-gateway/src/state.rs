// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

use abi::blob_gateway::BlobData;
use async_graphql::SimpleObject;
use linera_sdk::{
    linera_base_types::CryptoHash,
    views::{linera_views, MapView, RootView, ViewStorageContext},
};

#[derive(RootView, SimpleObject)]
#[view(context = ViewStorageContext)]
pub struct BlobGatewayState {
    pub blobs: MapView<CryptoHash, BlobData>,
}

pub mod adapter;
pub mod errors;
pub mod state_impl;
