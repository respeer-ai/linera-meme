use super::*;
use abi::{
    meme::{Meme, Metadata, MiningInfo},
    store_type::StoreType,
};
use async_graphql::{Request, Value, Variables};
use linera_sdk::{
    linera_base_types::{
        Account, AccountOwner, Amount, ApplicationId, ChainId, CryptoHash, TestString, Timestamp,
    },
    views::View,
};
use serde_json::json;
use std::{collections::HashMap, str::FromStr, sync::Arc};

fn chain_id() -> ChainId {
    ChainId::from_str("899dd894c41297e9dd1221fa02845efc81ed8abd9a0b7d203ad514b3aa6b2d46").unwrap()
}

fn owner() -> Account {
    Account {
        chain_id: chain_id(),
        owner: AccountOwner::from_str(
            "0x02e900512d2fca22897f80a2f6932ff454f2752ef7afad18729dd25e5b5b6e00",
        )
        .unwrap(),
    }
}

fn spender() -> Account {
    Account {
        chain_id: chain_id(),
        owner: AccountOwner::from_str(
            "0x5279b3ae14d3b38e14b65a74aefe44824ea88b25c7841836e9ec77d991a5bc8f",
        )
        .unwrap(),
    }
}

fn business_application_id() -> ApplicationId {
    ApplicationId::from_str("b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bad")
        .unwrap()
}

fn proxy_application_id() -> ApplicationId {
    ApplicationId::from_str("b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bae")
        .unwrap()
}

fn swap_application_id() -> ApplicationId {
    ApplicationId::from_str("b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5baf")
        .unwrap()
}

fn test_amount() -> Amount {
    Amount::from_tokens(100)
}

fn test_meme() -> Meme {
    Meme {
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
    }
}

fn test_mining_info() -> MiningInfo {
    MiningInfo::new(Amount::from_tokens(1000), Timestamp::from(1))
}

async fn state() -> MemeState {
    let runtime = ServiceRuntime::<MemeStateService>::new();
    let mut state = MemeState::load(runtime.root_view_storage_context())
        .await
        .expect("Failed to load meme state v1");

    state
        .business_application_id
        .set(Some(business_application_id()));
    state.operator.set(Some(owner()));
    state.initial_owner_balance.set(test_amount());
    state.owner.set(Some(owner()));
    state.holder.set(Some(owner()));
    state.meme.set(Some(test_meme()));
    state.proxy_application_id.set(Some(proxy_application_id()));
    state.swap_application_id.set(Some(swap_application_id()));
    state.mining_info.set(Some(test_mining_info()));

    state
}

fn account_variables(account: Account) -> Variables {
    Variables::from_json(json!({
        "owner": {
            "chain_id": account.chain_id.to_string(),
            "owner": account.owner.to_string(),
        }
    }))
}

#[tokio::test(flavor = "multi_thread")]
async fn health_query_returns_true() {
    let service = MemeStateService {
        state: Arc::new(state().await),
    };

    let response = service.handle_query(Request::new("{ health }")).await;
    let expected = Response::new(Value::from_json(json!({ "health": true })).unwrap());

    assert_eq!(response, expected);
}

#[tokio::test(flavor = "multi_thread")]
async fn owner_query_reads_register() {
    let service = MemeStateService {
        state: Arc::new(state().await),
    };

    let response = service.handle_query(Request::new("{ owner }")).await;
    let expected = Response::new(Value::from_json(json!({ "owner": owner() })).unwrap());

    assert_eq!(response, expected);
}

#[tokio::test(flavor = "multi_thread")]
async fn balance_query_reads_balance_map() {
    let mut state = state().await;
    state
        .balances
        .insert(&owner(), test_amount())
        .expect("Failed to set balance");

    let service = MemeStateService {
        state: Arc::new(state),
    };
    let request = Request::new("query Balance($owner: Account!) { balance(owner: $owner) }")
        .variables(account_variables(owner()));

    let response = service.handle_query(request).await;
    let expected = Response::new(Value::from_json(json!({ "balance": test_amount() })).unwrap());

    assert_eq!(response, expected);
}

#[tokio::test(flavor = "multi_thread")]
async fn allowance_query_reads_allowance_map() {
    let mut state = state().await;
    let mut allowances = HashMap::new();
    allowances.insert(spender(), test_amount());
    state
        .allowances
        .insert(&owner(), allowances)
        .expect("Failed to set allowance");

    let service = MemeStateService {
        state: Arc::new(state),
    };
    let request = Request::new(
        "query Allowance($owner: Account!, $spender: Account!) { allowance(owner: $owner, spender: $spender) }",
    )
    .variables(
        Variables::from_json(json!({
            "owner": {
                "chain_id": owner().chain_id.to_string(),
                "owner": owner().owner.to_string(),
            },
            "spender": {
                "chain_id": spender().chain_id.to_string(),
                "owner": spender().owner.to_string(),
            }
        })),
    );

    let response = service.handle_query(request).await;
    let expected = Response::new(Value::from_json(json!({ "allowance": test_amount() })).unwrap());

    assert_eq!(response, expected);
}

#[tokio::test(flavor = "multi_thread")]
async fn mining_info_query_reads_register() {
    let service = MemeStateService {
        state: Arc::new(state().await),
    };

    let response = service
        .handle_query(Request::new(
            "{ miningInfo { miningStarted target initialTarget } }",
        ))
        .await;
    let expected = Response::new(
        Value::from_json(json!({
            "miningInfo": {
                "miningStarted": false,
                "target": test_mining_info().target,
                "initialTarget": test_mining_info().initial_target,
            }
        }))
        .unwrap(),
    );

    assert_eq!(response, expected);
}

#[tokio::test(flavor = "multi_thread")]
async fn proxy_application_id_query_reads_register() {
    let service = MemeStateService {
        state: Arc::new(state().await),
    };

    let response = service
        .handle_query(Request::new("{ proxyApplicationId }"))
        .await;
    let expected = Response::new(
        Value::from_json(json!({ "proxyApplicationId": proxy_application_id() })).unwrap(),
    );

    assert_eq!(response, expected);
}

#[tokio::test(flavor = "multi_thread")]
async fn swap_application_id_query_reads_register() {
    let service = MemeStateService {
        state: Arc::new(state().await),
    };

    let response = service
        .handle_query(Request::new("{ swapApplicationId }"))
        .await;
    let expected = Response::new(
        Value::from_json(json!({ "swapApplicationId": swap_application_id() })).unwrap(),
    );

    assert_eq!(response, expected);
}

#[tokio::test(flavor = "multi_thread")]
async fn initial_owner_balance_query_reads_register() {
    let service = MemeStateService {
        state: Arc::new(state().await),
    };

    let response = service
        .handle_query(Request::new("{ initialOwnerBalance }"))
        .await;
    let expected =
        Response::new(Value::from_json(json!({ "initialOwnerBalance": test_amount() })).unwrap());

    assert_eq!(response, expected);
}

#[tokio::test(flavor = "multi_thread")]
async fn meme_query_reads_register() {
    let service = MemeStateService {
        state: Arc::new(state().await),
    };

    let response = service
        .handle_query(Request::new("{ meme { name ticker decimals } }"))
        .await;
    let expected = Response::new(
        Value::from_json(json!({
            "meme": {
                "name": "Test Token",
                "ticker": "LTT",
                "decimals": 6,
            }
        }))
        .unwrap(),
    );

    assert_eq!(response, expected);
}

#[tokio::test(flavor = "multi_thread")]
async fn total_supply_query_reads_meme_register() {
    let service = MemeStateService {
        state: Arc::new(state().await),
    };

    let response = service.handle_query(Request::new("{ totalSupply }")).await;
    let expected = Response::new(
        Value::from_json(json!({ "totalSupply": test_meme().total_supply })).unwrap(),
    );

    assert_eq!(response, expected);
}
