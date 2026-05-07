use super::super::{ProxyService, ProxyState};
use abi::{
    meme::{
        Liquidity, Metadata,
    },
    proxy::ProxyOperation,
    store_type::StoreType,
};

use std::sync::Arc;

use async_graphql::{Request, Response, Value};
use futures::FutureExt as _;
use linera_sdk::{
    linera_base_types::{
        Account, AccountOwner, Amount, ApplicationId, ChainId, CryptoHash, ModuleId,
    },
    util::BlockingWait,
    views::View,
    Service, ServiceRuntime,
};
use serde_json::json;
use std::{panic::AssertUnwindSafe, str::FromStr};

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

fn sample_create_meme_request() -> Request {
    let creator = Account {
        chain_id: ChainId::from_str(
            "f97a1e3237fb79ec600d691353466705c6c24b7b7f25cf1ba45c87bdbf75a75c",
        )
        .unwrap(),
        owner: AccountOwner::from_str(
            "0x8ee766a2e048e8f47851d176fb0a5115fcb669411ecf52c9dc2b88580e56efd0",
        )
        .unwrap(),
    };
    let blob_gateway_application_id = ApplicationId::from_str(
        "a93b53e910d6315a4d434cf1e7ccb303a5f1e7086a1c0841aba2586f275605fd",
    )
    .unwrap();
    let ams_application_id = ApplicationId::from_str(
        "3ad58a7d0ebab07cdb7fd335c5f5b91f499ac8db409d1090b0e75051f8eed42b",
    )
    .unwrap();
    let swap_application_id = ApplicationId::from_str(
        "27b9d4877d72f287adf99e928f6fb9e0c531aceb1657b2ddba6649abee05a4e0",
    )
    .unwrap();
    let swap_creator_chain_id = ChainId::from_str(
        "40338f2ac6faed71b91177156cb50831b175fe469eaccf5fdd7300b2d41d457e",
    )
    .unwrap();
    let logo_hash =
        CryptoHash::from_str("67f81b16f9303d3e95fd9a8634f06294addd8788ff5f789d2872a12490b03704")
            .unwrap();

    Request::new(
        r#"
        mutation CreateMeme(
          $memeInstantiationArgument: InstantiationArgument!,
          $memeParameters: MemeParameters!
        ) {
          createMeme(
            memeInstantiationArgument: $memeInstantiationArgument,
            memeParameters: $memeParameters
          )
        }
        "#,
    )
    .variables(async_graphql::Variables::from_json(json!({
        "memeInstantiationArgument": {
            "meme": {
                "initialSupply": "21000000.",
                "totalSupply": "21000000.",
                "name": "Test Local Meme",
                "ticker": "TLM",
                "decimals": 6,
                "metadata": {
                    "logoStoreType": "Blob",
                    "logo": logo_hash,
                    "description": "local mutation test",
                    "twitter": null,
                    "telegram": null,
                    "discord": null,
                    "website": null,
                    "github": null,
                    "liveStream": null
                },
                "virtualInitialLiquidity": true,
                "initialLiquidity": null
            },
            "blobGatewayApplicationId": blob_gateway_application_id,
            "amsApplicationId": ams_application_id,
            "proxyApplicationId": null,
            "swapApplicationId": swap_application_id
        },
        "memeParameters": {
            "creator": creator,
            "initialLiquidity": {
                "fungibleAmount": "10499900.",
                "nativeAmount": "8720."
            },
            "virtualInitialLiquidity": true,
            "swapCreatorChainId": swap_creator_chain_id,
            "enableMining": false,
            "miningSupply": "10499100."
        }
    })))
}

#[test]
fn create_meme_mutation_rejects_creator_chain() {
    let runtime = Arc::new(ServiceRuntime::<ProxyService>::new());
    let creator_chain = ChainId::from_str(
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    )
    .unwrap();
    runtime.set_chain_id(creator_chain);
    runtime.set_application_creator_chain_id(creator_chain);
    let state = ProxyState::load(runtime.root_view_storage_context())
        .blocking_wait()
        .expect("Failed to read from mock key value store");

    let service = ProxyService {
        state: Arc::new(state),
        runtime,
    };
    let request = sample_create_meme_request();

    let panic = AssertUnwindSafe(async move { service.handle_query(request).await })
        .catch_unwind()
        .now_or_never()
        .expect("Query should not await anything")
        .expect_err("creator chain mutation should panic");

    let message = if let Some(message) = panic.downcast_ref::<&str>() {
        (*message).to_string()
    } else if let Some(message) = panic.downcast_ref::<String>() {
        message.clone()
    } else {
        panic!("unexpected panic payload");
    };
    assert!(message.contains("Permission denied"));
}

#[test]
fn create_meme_mutation_schedules_operation_on_user_chain() {
    let runtime = Arc::new(ServiceRuntime::<ProxyService>::new());
    let creator_chain = ChainId::from_str(
        "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    )
    .unwrap();
    let other_chain = ChainId::from_str(
        "1111111111111111111111111111111111111111111111111111111111111111",
    )
    .unwrap();
    runtime.set_chain_id(other_chain);
    runtime.set_application_creator_chain_id(creator_chain);
    let state = ProxyState::load(runtime.root_view_storage_context())
        .blocking_wait()
        .expect("Failed to read from mock key value store");

    let service = ProxyService {
        state: Arc::new(state),
        runtime: runtime.clone(),
    };
    let request = sample_create_meme_request();

    let response = service
        .handle_query(request)
        .now_or_never()
        .expect("Query should not await anything");

    assert!(response.errors.is_empty(), "unexpected graphql errors: {:?}", response.errors);
    let scheduled = runtime.scheduled_operations::<ProxyOperation>();
    assert_eq!(scheduled.len(), 1);
    let ProxyOperation::CreateMeme {
        meme_instantiation_argument,
        meme_parameters,
    } = &scheduled[0]
    else {
        panic!("unexpected operation variant");
    };

    assert_eq!(meme_instantiation_argument.meme.name, "Test Local Meme");
    assert_eq!(meme_instantiation_argument.meme.ticker, "TLM");
    assert_eq!(
        meme_instantiation_argument.meme.initial_supply,
        Amount::from_tokens(21_000_000)
    );
    assert_eq!(
        meme_instantiation_argument.meme.total_supply,
        Amount::from_tokens(21_000_000)
    );
    assert_eq!(meme_instantiation_argument.meme.decimals, 6);
    assert_eq!(
        meme_instantiation_argument.meme.metadata,
        Metadata {
            logo_store_type: StoreType::Blob,
            logo: Some(
                CryptoHash::from_str(
                    "67f81b16f9303d3e95fd9a8634f06294addd8788ff5f789d2872a12490b03704",
                )
                .unwrap(),
            ),
            description: "local mutation test".to_string(),
            twitter: None,
            telegram: None,
            discord: None,
            website: None,
            github: None,
            live_stream: None,
        }
    );
    assert_eq!(meme_instantiation_argument.meme.virtual_initial_liquidity, true);
    assert_eq!(meme_instantiation_argument.meme.initial_liquidity, None);
    assert_eq!(
        meme_instantiation_argument.blob_gateway_application_id,
        Some(
            ApplicationId::from_str(
                "a93b53e910d6315a4d434cf1e7ccb303a5f1e7086a1c0841aba2586f275605fd",
            )
            .unwrap(),
        )
    );
    assert_eq!(
        meme_instantiation_argument.ams_application_id,
        Some(
            ApplicationId::from_str(
                "3ad58a7d0ebab07cdb7fd335c5f5b91f499ac8db409d1090b0e75051f8eed42b",
            )
            .unwrap(),
        )
    );
    assert_eq!(meme_instantiation_argument.proxy_application_id, None);
    assert_eq!(
        meme_instantiation_argument.swap_application_id,
        Some(
            ApplicationId::from_str(
                "27b9d4877d72f287adf99e928f6fb9e0c531aceb1657b2ddba6649abee05a4e0",
            )
            .unwrap(),
        )
    );

    assert_eq!(
        meme_parameters.creator,
        Account {
            chain_id: ChainId::from_str(
                "f97a1e3237fb79ec600d691353466705c6c24b7b7f25cf1ba45c87bdbf75a75c",
            )
            .unwrap(),
            owner: AccountOwner::from_str(
                "0x8ee766a2e048e8f47851d176fb0a5115fcb669411ecf52c9dc2b88580e56efd0",
            )
            .unwrap(),
        }
    );
    assert_eq!(
        meme_parameters.initial_liquidity,
        Some(Liquidity {
            fungible_amount: Amount::from_tokens(10_499_900),
            native_amount: Amount::from_tokens(8_720),
        })
    );
    assert!(meme_parameters.virtual_initial_liquidity);
    assert_eq!(
        meme_parameters.swap_creator_chain_id,
        ChainId::from_str("40338f2ac6faed71b91177156cb50831b175fe469eaccf5fdd7300b2d41d457e")
            .unwrap()
    );
    assert!(!meme_parameters.enable_mining);
    assert_eq!(
        meme_parameters.mining_supply,
        Some(Amount::from_tokens(10_499_100))
    );
}
