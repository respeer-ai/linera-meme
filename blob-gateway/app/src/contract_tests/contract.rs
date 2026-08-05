use super::super::{BlobGatewayContract, BlobGatewayState};

use abi::{
    blob_gateway::{
        state_v1::{
            BlobGatewayStateAbi as BlobGatewayStateV1Abi, BlobGatewayStateV1Operation,
            BlobGatewayStateV1Response,
        },
        BlobData, BlobDataType, BlobGatewayAbi, BlobGatewayMessage, BlobGatewayOperation,
        BlobGatewayResponse,
    },
    store_type::StoreType,
};
use linera_sdk::{
    abi::ContractAbi,
    linera_base_types::{
        Account, AccountOwner, ApplicationId, ChainId, CryptoHash, TestString, Timestamp,
    },
    util::BlockingWait,
    views::View,
    Contract, ContractRuntime,
};
use std::{cell::RefCell, rc::Rc, str::FromStr};

struct TestSuite {
    contract: BlobGatewayContract,
}

impl TestSuite {
    fn new() -> Self {
        let runtime = ContractRuntime::new()
            .with_application_parameters(())
            .with_authenticated_signer(Self::creator_account().owner)
            .with_chain_id(Self::creator_account().chain_id)
            .with_application_creator_chain_id(Self::creator_account().chain_id)
            .with_system_time(Timestamp::from(1))
            .with_application_id(Self::blob_gateway_application_id().with_abi::<BlobGatewayAbi>());
        let mut contract = BlobGatewayContract {
            state: Rc::new(RefCell::new(
                BlobGatewayState::load(runtime.root_view_storage_context())
                    .blocking_wait()
                    .expect("Failed to read from mock key value store"),
            )),
            runtime: Rc::new(RefCell::new(runtime)),
        };

        contract.instantiate(()).blocking_wait();

        Self { contract }
    }

    async fn execute_operation(&mut self, operation: BlobGatewayOperation) -> BlobGatewayResponse {
        self.contract.execute_operation(operation).await
    }

    async fn execute_message(&mut self, message: BlobGatewayMessage) {
        self.contract.execute_message(message).await;
    }

    fn append_state(&mut self) {
        self.contract
            .state
            .borrow_mut()
            .state_applications
            .insert(&1, Self::state_application_id())
            .expect("Failed to insert state application");
        self.contract.state.borrow_mut().latest_state_version.set(1);
    }

    fn blob_gateway_application_id() -> ApplicationId {
        Self::application_id("b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bad")
    }

    fn state_application_id() -> ApplicationId {
        Self::application_id("b20ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bad")
    }

    fn other_application_id() -> ApplicationId {
        Self::application_id("b30ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bad")
    }

    fn application_id(value: &str) -> ApplicationId {
        ApplicationId::from_str(value).unwrap()
    }

    fn creator_account() -> Account {
        Account {
            chain_id: ChainId::from_str(
                "aee928d4bf3880353b4a3cd9b6f88e6cc6e5ed050860abae439e7782e9b2dfe8",
            )
            .unwrap(),
            owner: AccountOwner::from_str(
                "0x02e900512d2fca22897f80a2f6932ff454f2752ef7afad18729dd25e5b5b6e00",
            )
            .unwrap(),
        }
    }

    fn other_account() -> Account {
        Account {
            chain_id: ChainId::from_str(
                "abdb7c1079f36eaa03f629540283a881eb4256d1ece83a84415022d4d2a9ac65",
            )
            .unwrap(),
            owner: AccountOwner::from_str(
                "0x02e900512d2fca22897f80a2f6932ff454f2752ef7afad18729dd25e5b5b6e09",
            )
            .unwrap(),
        }
    }

    fn test_hash(seed: &str) -> CryptoHash {
        CryptoHash::new(&TestString::new(seed.to_owned()))
    }

    fn test_blob_data(
        blob_hash: CryptoHash,
        store_type: StoreType,
        data_type: BlobDataType,
    ) -> BlobData {
        BlobData {
            store_type,
            data_type,
            blob_hash,
            creator: Self::creator_account(),
            created_at: Timestamp::from(1),
        }
    }
}

#[tokio::test(flavor = "multi_thread")]
async fn operation_register_queues_message_with_runtime_metadata() {
    let mut suite = TestSuite::new();
    let blob_hash = TestSuite::test_hash("blob-1");

    let response = suite
        .execute_operation(BlobGatewayOperation::Register {
            store_type: StoreType::S3,
            data_type: BlobDataType::Image,
            blob_hash,
        })
        .await;

    assert!(matches!(response, BlobGatewayResponse::Ok));

    let runtime = suite.contract.runtime.borrow();
    let requests = runtime.created_send_message_requests();

    assert_eq!(requests.len(), 1);
    assert_eq!(
        requests[0].destination,
        TestSuite::creator_account().chain_id
    );
    match &requests[0].message {
        BlobGatewayMessage::Register { blob_data } => {
            assert_eq!(
                blob_data,
                &BlobData {
                    store_type: StoreType::S3,
                    data_type: BlobDataType::Image,
                    blob_hash,
                    creator: TestSuite::creator_account(),
                    created_at: Timestamp::from(1),
                }
            );
        }
    }
}

#[tokio::test(flavor = "multi_thread")]
async fn operation_append_state_records_state_v1_application() {
    let mut suite = TestSuite::new();

    let response = suite
        .execute_operation(BlobGatewayOperation::AppendState {
            state_application_id: TestSuite::state_application_id(),
        })
        .await;

    assert!(matches!(response, BlobGatewayResponse::Ok));
    assert_eq!(suite.contract.state.borrow().latest_state_version.get(), &1);
    assert_eq!(
        suite
            .contract
            .state
            .borrow()
            .state_applications
            .get(&1)
            .blocking_wait()
            .unwrap(),
        Some(TestSuite::state_application_id())
    );
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic(expected = "Only allow application creator")]
async fn operation_append_state_rejects_non_creator_chain() {
    let mut suite = TestSuite::new();
    suite
        .contract
        .runtime
        .borrow_mut()
        .set_chain_id(TestSuite::other_account().chain_id);

    suite
        .execute_operation(BlobGatewayOperation::AppendState {
            state_application_id: TestSuite::state_application_id(),
        })
        .await;
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic(expected = "invalid state version")]
async fn operation_append_state_rejects_second_state_version() {
    let mut suite = TestSuite::new();
    suite.append_state();

    suite
        .execute_operation(BlobGatewayOperation::AppendState {
            state_application_id: TestSuite::other_application_id(),
        })
        .await;
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic(expected = "state application already exists")]
async fn operation_append_state_rejects_duplicate_state_application_id() {
    let mut suite = TestSuite::new();
    suite.append_state();

    suite
        .execute_operation(BlobGatewayOperation::AppendState {
            state_application_id: TestSuite::state_application_id(),
        })
        .await;
}

#[tokio::test(flavor = "multi_thread")]
async fn operation_handoff_calls_state_v1_handoff() {
    let mut suite = TestSuite::new();
    suite.append_state();
    let new_business_application_id = TestSuite::other_application_id();

    suite
        .contract
        .runtime
        .borrow_mut()
        .set_call_application_handler(move |authenticated, application_id, call| {
            assert!(authenticated);
            assert_eq!(application_id, TestSuite::state_application_id());
            assert_eq!(
                BlobGatewayStateV1Abi::deserialize_operation(call).unwrap(),
                BlobGatewayStateV1Operation::Handoff {
                    new_business_application_id,
                }
            );
            BlobGatewayStateV1Abi::serialize_response(BlobGatewayStateV1Response::Ok).unwrap()
        });

    suite
        .execute_operation(BlobGatewayOperation::Handoff {
            new_business_application_id,
        })
        .await;
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic(expected = "invalid state version")]
async fn operation_handoff_rejects_missing_state_v1_append() {
    let mut suite = TestSuite::new();

    suite
        .execute_operation(BlobGatewayOperation::Handoff {
            new_business_application_id: TestSuite::other_application_id(),
        })
        .await;
}

#[tokio::test(flavor = "multi_thread")]
async fn message_register_calls_state_v1_create_blob() {
    let mut suite = TestSuite::new();
    suite.append_state();
    let blob_data = TestSuite::test_blob_data(
        TestSuite::test_hash("blob-2"),
        StoreType::Ipfs,
        BlobDataType::Html,
    );

    let expected_blob_data = blob_data.clone();
    suite
        .contract
        .runtime
        .borrow_mut()
        .set_call_application_handler(move |authenticated, application_id, call| {
            assert!(authenticated);
            assert_eq!(application_id, TestSuite::state_application_id());
            assert_eq!(
                BlobGatewayStateV1Abi::deserialize_operation(call).unwrap(),
                BlobGatewayStateV1Operation::CreateBlob {
                    blob_data: expected_blob_data.clone(),
                }
            );
            BlobGatewayStateV1Abi::serialize_response(BlobGatewayStateV1Response::Ok).unwrap()
        });

    suite
        .execute_message(BlobGatewayMessage::Register {
            blob_data: blob_data.clone(),
        })
        .await;
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic(expected = "state application does not exist")]
async fn message_register_rejects_missing_state_v1_append() {
    let mut suite = TestSuite::new();
    let blob_data = TestSuite::test_blob_data(
        TestSuite::test_hash("blob-3"),
        StoreType::S3,
        BlobDataType::Raw,
    );

    suite
        .execute_message(BlobGatewayMessage::Register { blob_data })
        .await;
}

#[tokio::test(flavor = "multi_thread")]
async fn operation_set_operator_calls_state_v1_set_operator() {
    let mut suite = TestSuite::new();
    suite.append_state();
    let new_operator = TestSuite::other_account();

    suite
        .contract
        .runtime
        .borrow_mut()
        .set_call_application_handler(move |authenticated, application_id, call| {
            assert!(authenticated);
            assert_eq!(application_id, TestSuite::state_application_id());
            assert_eq!(
                BlobGatewayStateV1Abi::deserialize_operation(call).unwrap(),
                BlobGatewayStateV1Operation::SetOperator { new_operator }
            );
            BlobGatewayStateV1Abi::serialize_response(BlobGatewayStateV1Response::Ok).unwrap()
        });

    suite
        .execute_operation(BlobGatewayOperation::SetOperator { new_operator })
        .await;
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic(expected = "Only allow application creator")]
async fn operation_set_operator_rejects_non_creator_chain() {
    let mut suite = TestSuite::new();
    suite
        .contract
        .runtime
        .borrow_mut()
        .set_chain_id(TestSuite::other_account().chain_id);

    suite
        .execute_operation(BlobGatewayOperation::SetOperator {
            new_operator: TestSuite::other_account(),
        })
        .await;
}
