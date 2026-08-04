use abi::{
    meme::{InstantiationArgument, Meme, MemeAbi, Metadata},
    store_type::StoreType,
};
use async_graphql::{Request, Response, Value};
use futures::FutureExt as _;
use linera_sdk::{
    linera_base_types::{
        Account, AccountOwner, Amount, ApplicationId, ChainId, CryptoHash, TestString, Timestamp,
    },
    util::BlockingWait,
    views::View,
    Service, ServiceRuntime,
};
use meme_app::state::MemeState as BusinessState;
use meme_state::{interfaces::state::StateInterface, state::MemeState as StateAppState};
use serde_json::json;
use std::{str::FromStr, sync::Arc};

use crate::MemeService;

#[tokio::test(flavor = "multi_thread")]
async fn query() {
    let business_application_id =
        ApplicationId::from_str("b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bad")
            .unwrap();
    let state_application_id =
        ApplicationId::from_str("b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bae")
            .unwrap();

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
    let application = Account {
        chain_id,
        owner: AccountOwner::from(state_application_id),
    };

    let initial_supply = Amount::from_tokens(21000000);
    let instantiation_argument = InstantiationArgument {
        meme: Meme {
            name: "Test Token".to_string(),
            ticker: "LTT".to_string(),
            decimals: 6,
            initial_supply,
            total_supply: initial_supply,
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
        swap_application_id: Some(state_application_id),
    };

    // Build the state app directly; the business service will query it through the
    // mocked `query_application` handler.
    let mut state_app_state = StateAppState::load(
        ServiceRuntime::<MemeService>::new()
            .root_view_storage_context(),
    )
    .blocking_wait()
    .expect("Failed to load meme state v1");
    state_app_state.instantiate(abi::meme::StateInstantiationArgument {
        business_application_id,
        operator: Some(owner),
        proxy_application_id: None,
    });
    let now = Timestamp::now();
    state_app_state
        .initialize(abi::meme::InitializeArgument {
            owner,
            holder: application,
            meme: instantiation_argument.meme.clone(),
            initial_owner_balance: Amount::from_tokens(100),
            blob_gateway_application_id: None,
            ams_application_id: None,
            swap_application_id: Some(state_application_id),
            enable_mining: false,
            mining_supply: None,
            now,
        })
        .await
        .expect("Failed to initialize meme state v1");
    let total_supply = instantiation_argument.meme.total_supply;

    let runtime = Arc::new(
        ServiceRuntime::<MemeService>::new()
            .with_system_time(Timestamp::now())
            .with_application_id(business_application_id.with_abi::<MemeAbi>())
            .with_application_creator_chain_id(chain_id)
            .with_query_application_handler(move |_application_id: ApplicationId, query: Vec<u8>| {
                let request: Request = serde_json::from_slice(&query).unwrap();
                if request.query.contains("totalSupply") {
                    serde_json::to_vec(&Response::new(
                        Value::from_json(json!({ "totalSupply": total_supply })).unwrap(),
                    ))
                    .unwrap()
                } else {
                    serde_json::to_vec(&Response::new(Value::Null)).unwrap()
                }
            }),
    );

    let mut business_state = BusinessState::load(runtime.root_view_storage_context())
        .blocking_wait()
        .expect("Failed to load meme business state");
    business_state
        .state_applications
        .insert(&1, state_application_id)
        .expect("Failed to set state application");
    business_state.latest_state_version.set(1);

    let service = MemeService {
        runtime,
        state: Arc::new(business_state),
    };
    let request = Request::new("{ totalSupply }");

    let response = service
        .handle_query(request)
        .now_or_never()
        .expect("Query should not await anything");

    let expected = Response::new(
        Value::from_json(json!({"totalSupply": instantiation_argument.meme.total_supply}))
            .unwrap(),
    );

    assert_eq!(response, expected);
}
