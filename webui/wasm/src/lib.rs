/**
This module defines the client API for the Web extension.

Exported (marked with `#[wasm_bindgen]`) functions will be callable from the extension frontend.

Exported functions prefixed with `dapp_` _will additionally be
callable from all Web pages to which the Web client has been
connected_.  Outside of their type, which is checked at call time,
arguments to these functions cannot be trusted and _must_ be verified!
*/
use async_graphql::{http::parse_query_string, EmptySubscription, Schema};

use wasm_bindgen::prelude::*;
use web_sys::*;

mod fake_proxy;
use fake_proxy::{MutationRoot as ProxyMutationRoot, QueryRoot as ProxyQueryRoot};

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
    Ok(format!("{:?}", values))
}
