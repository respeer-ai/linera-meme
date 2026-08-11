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
    let mut state_app_state =
        StateAppState::load(ServiceRuntime::<MemeService>::new().root_view_storage_context())
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
            .with_query_application_handler(
                move |_application_id: ApplicationId, query: Vec<u8>| {
                    let request: Request = serde_json::from_slice(&query).unwrap();
                    if request.query.contains("totalSupply") {
                        serde_json::to_vec(&Response::new(
                            Value::from_json(json!({ "totalSupply": total_supply })).unwrap(),
                        ))
                        .unwrap()
                    } else {
                        serde_json::to_vec(&Response::new(Value::Null)).unwrap()
                    }
                },
            ),
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
        Value::from_json(json!({"totalSupply": instantiation_argument.meme.total_supply})).unwrap(),
    );

    assert_eq!(response, expected);
}

#[cfg(test)]
mod extra_service_tests {
    use super::MemeService;
    use abi::{
        meme::{Meme, MemeAbi, MemeOperation, Metadata, MiningInfo},
        store_type::StoreType,
    };
    use async_graphql::{Request, Response, Value, Variables};
    use linera_sdk::{
        linera_base_types::{
            Account, AccountOwner, Amount, ApplicationId, ChainId, CryptoHash, TestString,
            Timestamp,
        },
        util::BlockingWait,
        views::View,
        Service, ServiceRuntime,
    };
    use meme_app::state::MemeState as BusinessState;
    use serde_json::json;
    use std::{str::FromStr, sync::Arc};

    fn chain_id() -> ChainId {
        ChainId::from_str("899dd894c41297e9dd1221fa02845efc81ed8abd9a0b7d203ad514b3aa6b2d46")
            .unwrap()
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

    fn business_application_id() -> ApplicationId {
        ApplicationId::from_str("b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bad")
            .unwrap()
    }

    fn state_application_id() -> ApplicationId {
        ApplicationId::from_str("b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bae")
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

    fn runtime() -> Arc<ServiceRuntime<MemeService>> {
        Arc::new(
            ServiceRuntime::<MemeService>::new()
                .with_application_id(business_application_id().with_abi::<MemeAbi>())
                .with_application_creator_chain_id(chain_id()),
        )
    }

    fn runtime_with_state_query(
        mut response_for_query: impl FnMut(&str) -> Response + Send + 'static,
    ) -> Arc<ServiceRuntime<MemeService>> {
        let runtime = ServiceRuntime::<MemeService>::new()
            .with_application_id(business_application_id().with_abi::<MemeAbi>())
            .with_application_creator_chain_id(chain_id())
            .with_query_application_handler(move |application_id, query| {
                assert_eq!(application_id, state_application_id());
                let request: Request = serde_json::from_slice(&query).unwrap();
                let query_name = if request.query.contains("meme {") {
                    "meme"
                } else if request.query.contains("miningInfo {") {
                    "miningInfo"
                } else if request.query.contains("totalSupply") {
                    "totalSupply"
                } else if request.query.contains("balance") {
                    "balance"
                } else if request.query.contains("allowance") {
                    "allowance"
                } else if request.query.contains("proxyApplicationId") {
                    "proxyApplicationId"
                } else if request.query.contains("swapApplicationId") {
                    "swapApplicationId"
                } else if request.query.contains("initialOwnerBalance") {
                    "initialOwnerBalance"
                } else {
                    panic!("Unexpected state app query: {}", request.query)
                };
                serde_json::to_vec(&response_for_query(query_name)).unwrap()
            });
        Arc::new(runtime)
    }

    fn service_with_runtime(runtime: Arc<ServiceRuntime<MemeService>>) -> MemeService {
        let mut state = BusinessState::load(runtime.root_view_storage_context())
            .blocking_wait()
            .expect("Failed to load meme business state");
        state
            .state_applications
            .insert(&1, state_application_id())
            .expect("Failed to set state application");
        state.latest_state_version.set(1);
        MemeService {
            runtime,
            state: Arc::new(state),
        }
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
        let service = service_with_runtime(runtime());

        let response = service.handle_query(Request::new("{ health }")).await;
        let expected = Response::new(Value::from_json(json!({ "health": true })).unwrap());

        assert_eq!(response, expected);
    }

    #[tokio::test(flavor = "multi_thread")]
    async fn creator_chain_id_query_reads_runtime() {
        let service = service_with_runtime(runtime());

        let response = service
            .handle_query(Request::new("{ creatorChainId }"))
            .await;
        let expected =
            Response::new(Value::from_json(json!({ "creatorChainId": chain_id() })).unwrap());

        assert_eq!(response, expected);
    }

    #[tokio::test(flavor = "multi_thread")]
    async fn balance_of_query_reads_state_application() {
        let runtime = runtime_with_state_query(|query_name| {
            assert_eq!(query_name, "balance");
            Response::new(Value::from_json(json!({ "balance": test_amount() })).unwrap())
        });
        let service = service_with_runtime(runtime);

        let request =
            Request::new("query BalanceOf($owner: Account!) { balanceOf(owner: $owner) }")
                .variables(account_variables(owner()));

        let response = service.handle_query(request).await;
        let expected =
            Response::new(Value::from_json(json!({ "balanceOf": test_amount() })).unwrap());

        assert_eq!(response, expected);
    }

    #[tokio::test(flavor = "multi_thread")]
    async fn allowance_of_query_reads_state_application() {
        let spender = owner();
        let runtime = runtime_with_state_query(|query_name| {
            assert_eq!(query_name, "allowance");
            Response::new(Value::from_json(json!({ "allowance": test_amount() })).unwrap())
        });
        let service = service_with_runtime(runtime);

        let request = Request::new(
            "query AllowanceOf($owner: Account!, $spender: Account!) { allowanceOf(owner: $owner, spender: $spender) }",
        )
        .variables(
            Variables::from_json(json!({
                "owner": {
                    "chain_id": owner().chain_id.to_string(),
                    "owner": owner().owner.to_string(),
                },
                "spender": {
                    "chain_id": spender.chain_id.to_string(),
                    "owner": spender.owner.to_string(),
                }
            })),
        );

        let response = service.handle_query(request).await;
        let expected =
            Response::new(Value::from_json(json!({ "allowanceOf": test_amount() })).unwrap());

        assert_eq!(response, expected);
    }

    #[tokio::test(flavor = "multi_thread")]
    async fn initial_owner_balance_query_reads_state_application() {
        let runtime = runtime_with_state_query(|query_name| {
            assert_eq!(query_name, "initialOwnerBalance");
            Response::new(
                Value::from_json(json!({ "initialOwnerBalance": test_amount() })).unwrap(),
            )
        });
        let service = service_with_runtime(runtime);

        let response = service
            .handle_query(Request::new("{ initialOwnerBalance }"))
            .await;
        let expected = Response::new(
            Value::from_json(json!({ "initialOwnerBalance": test_amount() })).unwrap(),
        );

        assert_eq!(response, expected);
    }

    #[tokio::test(flavor = "multi_thread")]
    async fn meme_query_reads_state_application() {
        let runtime = runtime_with_state_query(|query_name| {
            assert_eq!(query_name, "meme");
            Response::new(Value::from_json(json!({ "meme": test_meme() })).unwrap())
        });
        let service = service_with_runtime(runtime);

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
    async fn mining_info_query_reads_state_application() {
        let runtime = runtime_with_state_query(|query_name| {
            assert_eq!(query_name, "miningInfo");
            Response::new(Value::from_json(json!({ "miningInfo": test_mining_info() })).unwrap())
        });
        let service = service_with_runtime(runtime);

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
    async fn mint_mutation_schedules_operation() {
        let runtime = runtime();
        let service = service_with_runtime(runtime.clone());
        let to = owner();
        let amount = test_amount();

        let request = Request::new(
            "mutation Mint($to: Account!, $amount: Amount!) { mint(to: $to, amount: $amount) }",
        )
        .variables(Variables::from_json(json!({
            "to": {
                "chain_id": to.chain_id.to_string(),
                "owner": to.owner.to_string(),
            },
            "amount": amount,
        })));

        let response = service.handle_query(request).await;
        let expected = Response::new(Value::from_json(json!({ "mint": [] })).unwrap());
        assert_eq!(response, expected);

        let operations: Vec<MemeOperation> = runtime.scheduled_operations();
        assert_eq!(operations.len(), 1);
        assert!(
            matches!(
                &operations[0],
                MemeOperation::Mint { to: op_to, amount: op_amount }
                    if op_to == &to && op_amount == &amount
            ),
            "unexpected scheduled operation: {:?}",
            operations[0]
        );
    }

    #[tokio::test(flavor = "multi_thread")]
    async fn mine_mutation_schedules_operation() {
        let runtime = runtime();
        let service = service_with_runtime(runtime.clone());
        let nonce = CryptoHash::new(&TestString::new("test-nonce".to_string()));

        let response = service
            .handle_query(Request::new(format!(
                "mutation {{ mine(nonce: \"{}\") }}",
                nonce
            )))
            .await;
        let expected = Response::new(Value::from_json(json!({ "mine": [] })).unwrap());
        assert_eq!(response, expected);

        let operations: Vec<MemeOperation> = runtime.scheduled_operations();
        assert_eq!(operations.len(), 1);
        assert!(
            matches!(
                &operations[0],
                MemeOperation::Mine { nonce: op_nonce } if op_nonce == &nonce
            ),
            "unexpected scheduled operation: {:?}",
            operations[0]
        );
    }

    #[tokio::test(flavor = "multi_thread")]
    async fn redeem_mutation_schedules_operation() {
        let runtime = runtime();
        let service = service_with_runtime(runtime.clone());
        let amount = test_amount();

        let response = service
            .handle_query(Request::new(format!(
                "mutation {{ redeem(amount: \"{}\") }}",
                amount
            )))
            .await;
        let expected = Response::new(Value::from_json(json!({ "redeem": [] })).unwrap());
        assert_eq!(response, expected);

        let operations: Vec<MemeOperation> = runtime.scheduled_operations();
        assert_eq!(operations.len(), 1);
        assert!(
            matches!(
                &operations[0],
                MemeOperation::Redeem { amount: op_amount } if op_amount == &Some(amount)
            ),
            "unexpected scheduled operation: {:?}",
            operations[0]
        );
    }
}
