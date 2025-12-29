use super::super::{ProxyService, ProxyState};

use std::sync::Arc;

use async_graphql::{Request, Response, Value};
use futures::FutureExt as _;
use linera_sdk::{
    linera_base_types::ModuleId, util::BlockingWait, views::View, Service, ServiceRuntime,
};
use serde_json::json;
use std::str::FromStr;

#[test]
fn query() {
    let meme_bytecode_id = ModuleId::from_str("b94e486abcfc016e937dad4297523060095f405530c95d498d981a94141589f167693295a14c3b48460ad6f75d67d2414428227550eb8cee8ecaa37e8646518300").unwrap();
    let runtime = Arc::new(ServiceRuntime::<ProxyService>::new());
    let mut state = ProxyState::load(runtime.root_view_storage_context())
        .blocking_wait()
        .expect("Failed to read from mock key value store");
    state.meme_bytecode_id.set(Some(meme_bytecode_id));

    let service = ProxyService {
        state: Arc::new(state),
        runtime,
    };
    let request = Request::new("{ memeBytecodeId }");

    let response = service
        .handle_query(request)
        .now_or_never()
        .expect("Query should not await anything");

    let expected =
        Response::new(Value::from_json(json!({"memeBytecodeId": meme_bytecode_id})).unwrap());

    assert_eq!(response, expected)
}
