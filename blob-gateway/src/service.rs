// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

#![cfg_attr(target_arch = "wasm32", no_main)]

mod state;

use std::sync::{Arc, Mutex};

use async_graphql::{Context, EmptyMutation, EmptySubscription, Object, Request, Response, Schema};
use linera_sdk::{
    linera_base_types::{DataBlobHash, Timestamp, WithServiceAbi},
    views::View,
    Service, ServiceRuntime,
};

use abi::blob_gateway::{BlobData, BlobDataType, BlobGatewayAbi};
use blob_gateway::BlobGatewayError;
use state::BlobGatewayState;

pub struct BlobGatewayService {
    state: Arc<BlobGatewayState>,
    runtime: Arc<Mutex<ServiceRuntime<BlobGatewayService>>>,
}

linera_sdk::service!(BlobGatewayService);

impl WithServiceAbi for BlobGatewayService {
    type Abi = BlobGatewayAbi;
}

struct FetchContext {
    state: Arc<BlobGatewayState>,
    runtime: Arc<Mutex<ServiceRuntime<BlobGatewayService>>>,
}

impl Service for BlobGatewayService {
    type Parameters = ();

    async fn new(runtime: ServiceRuntime<Self>) -> Self {
        let state = BlobGatewayState::load(runtime.root_view_storage_context())
            .await
            .expect("Failed to load state");
        BlobGatewayService {
            state: Arc::new(state),
            runtime: Arc::new(Mutex::new(runtime)),
        }
    }

    async fn handle_query(&self, request: Request) -> Response {
        let fetch_context = FetchContext {
            state: self.state.clone(),
            runtime: self.runtime.clone(),
        };

        let schema = Schema::build(QueryRoot {}, EmptyMutation, EmptySubscription)
            .data(fetch_context)
            .finish();
        schema.execute(request).await
    }
}

struct QueryRoot {}

#[Object]
impl QueryRoot {
    async fn fetch(
        &self,
        ctx: &Context<'_>,
        blob_hash: DataBlobHash,
    ) -> Result<Vec<u8>, BlobGatewayError> {
        let ctx = ctx.data::<FetchContext>().unwrap();
        Ok(ctx.runtime.lock().unwrap().read_data_blob(blob_hash))
    }

    async fn list(
        &self,
        ctx: &Context<'_>,
        created_before: Option<Timestamp>,
        created_after: Option<Timestamp>,
        data_type: Option<BlobDataType>,
        limit: usize,
    ) -> Result<Vec<BlobData>, BlobGatewayError> {
        let ctx = ctx.data::<FetchContext>().unwrap();
        let mut blobs: Vec<BlobData> = Vec::new();

        ctx.state
            .blobs
            .for_each_index_value_while(|_key, value| {
                if let Some(created_before) = created_before {
                    if value.created_at > created_before {
                        return Ok(true);
                    }
                }
                if let Some(created_after) = created_after {
                    if value.created_at < created_after {
                        return Ok(true);
                    }
                }
                if let Some(data_type) = data_type {
                    if data_type != value.data_type {
                        return Ok(true);
                    }
                }
                if limit > 0 && blobs.len() >= limit {
                    return Ok(false);
                }
                blobs.push(value.as_ref().clone());
                Ok(blobs.len() < limit)
            })
            .await?;

        blobs.sort_by(|a, b| b.created_at.cmp(&a.created_at));

        Ok(blobs)
    }
}
