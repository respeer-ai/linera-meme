use super::super::{MemeService, MemeState};
use meme::interfaces::state::StateInterface;

use std::sync::Arc;

use abi::{
    meme::{InstantiationArgument, Meme, Metadata},
    store_type::StoreType,
};
use async_graphql::{Request, Response, Value};
use futures::FutureExt as _;
use linera_sdk::{
    linera_base_types::{
        Account, AccountOwner, Amount, ApplicationId, ChainId, CryptoHash, TestString,
    },
    util::BlockingWait,
    views::View,
    Service, ServiceRuntime,
};
use serde_json::json;
use std::str::FromStr;

#[tokio::test(flavor = "multi_thread")]
async fn query() {
    let runtime = Arc::new(ServiceRuntime::<MemeService>::new());
    let mut state = MemeState::load(runtime.root_view_storage_context())
        .blocking_wait()
        .expect("Failed to read from mock key value store");

    let application_id =
        ApplicationId::from_str("b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bad")
            .unwrap();
    let instantiation_argument = InstantiationArgument {
        meme: Meme {
            name: "Test Token".to_string(),
            ticker: "LTT".to_string(),
            decimals: 6,
            initial_supply: Amount::from_tokens(21000000),
            total_supply: Amount::from_tokens(21000000),
            metadata: Metadata {
                logo_store_type: StoreType::S3,
                logo: Some(CryptoHash::new(&TestString::new("Test Logo".to_string()))),
                description: "Test token description".to_string(),
                twitter: None,
                telegram: None,
                discord: None,
                website: None,
                github: None,
                live_stream: None,
            },
            virtual_initial_liquidity: true,
            initial_liquidity: None,
        },
        blob_gateway_application_id: None,
        ams_application_id: None,
        proxy_application_id: None,
        swap_application_id: Some(application_id),
    };

    let chain_id =
        ChainId::from_str("899dd894c41297e9dd1221fa02845efc81ed8abd9a0b7d203ad514b3aa6b2d46")
            .unwrap();
    let owner = Account {
        chain_id,
        owner: AccountOwner::from_str(
            "0x02e900512d2fca22897f80a2f6932ff454f2752ef7afad18729dd25e5b5b6e00",
        )
        .unwrap(),
    };
    let application_id =
        ApplicationId::from_str("b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bae")
            .unwrap();
    let application = Account {
        chain_id,
        owner: AccountOwner::from(application_id),
    };
    state
        .instantiate(owner, application, instantiation_argument.clone())
        .expect("Failed inistantiate");

    let service = MemeService {
        state: Arc::new(state),
        runtime,
    };
    let request = Request::new("{ totalSupply }");

    let response = service
        .handle_query(request)
        .now_or_never()
        .expect("Query should not await anything");

    let expected = Response::new(
        Value::from_json(json!({"totalSupply" : instantiation_argument.meme.total_supply}))
            .unwrap(),
    );

    assert_eq!(response, expected)
}
