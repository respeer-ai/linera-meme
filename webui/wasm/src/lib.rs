/**
This module defines the client API for the Web extension.

Exported (marked with `#[wasm_bindgen]`) functions will be callable from the extension frontend.

Exported functions prefixed with `dapp_` _will additionally be
callable from all Web pages to which the Web client has been
connected_.  Outside of their type, which is checked at call time,
arguments to these functions cannot be trusted and _must_ be verified!
*/
use async_graphql::{http::parse_query_string, EmptySubscription, Schema};

use linera_base::{crypto::CryptoHash, data_types::BlobContent};

use wasm_bindgen::prelude::*;
use web_sys::*;

mod fake_proxy;
use fake_proxy::{MutationRoot as ProxyMutationRoot, QueryRoot as ProxyQueryRoot};

mod fake_swap;
use fake_swap::{MutationRoot as SwapMutationRoot, QueryRoot as SwapQueryRoot};

mod fake_pool;
use fake_pool::{MutationRoot as PoolMutationRoot, QueryRoot as PoolQueryRoot};

#[wasm_bindgen]
pub async fn graphql_deserialize_proxy_operation(
    query: &str,
    variables: &str,
) -> Result<String, JsError> {
    let request = parse_query_string(&format!("query={}&variables={}", query, variables))?;
    let schema = Schema::new(ProxyQueryRoot, ProxyMutationRoot, EmptySubscription);
    let value = schema.execute(request).await.into_result().unwrap().data;
    let async_graphql::Value::Object(object) = value else {
        todo!()
    };
    let values = object.values().collect::<Vec<&async_graphql::Value>>();
    if values.len() == 0 {
        todo!()
    }
    Ok(serde_json::to_string(&values[0])?)
}

#[wasm_bindgen]
pub async fn graphql_deserialize_pool_operation(
    query: &str,
    variables: &str,
) -> Result<String, JsError> {
    let request = parse_query_string(&format!("query={}&variables={}", query, variables))?;
    let schema = Schema::new(PoolQueryRoot, PoolMutationRoot, EmptySubscription);
    let value = schema.execute(request).await.into_result().unwrap().data;
    let async_graphql::Value::Object(object) = value else {
        todo!()
    };
    let values = object.values().collect::<Vec<&async_graphql::Value>>();
    if values.len() == 0 {
        todo!()
    }
    Ok(serde_json::to_string(&values[0])?)
}

#[wasm_bindgen]
pub async fn graphql_deserialize_swap_operation(
    query: &str,
    variables: &str,
) -> Result<String, JsError> {
    let request = parse_query_string(&format!("query={}&variables={}", query, variables))?;
    let schema = Schema::new(SwapQueryRoot, SwapMutationRoot, EmptySubscription);
    let value = schema.execute(request).await.into_result().unwrap().data;
    let async_graphql::Value::Object(object) = value else {
        todo!()
    };
    let values = object.values().collect::<Vec<&async_graphql::Value>>();
    if values.len() == 0 {
        todo!()
    }
    Ok(serde_json::to_string(&values[0])?)
}

#[wasm_bindgen]
pub async fn blob_hash(blob: &str) -> Result<String, JsError> {
    let bytes: Vec<u8> = serde_json::from_str(blob)?;
    Ok(CryptoHash::new(&BlobContent::new_data(bytes)).to_string())
}

#[wasm_bindgen(start)]
pub fn main() {
    std::panic::set_hook(Box::new(console_error_panic_hook::hook));
    linera_base::tracing::init();
    console_log::init_with_level(log::Level::Debug).unwrap();
    log::info!("Hello Linera!");
}
