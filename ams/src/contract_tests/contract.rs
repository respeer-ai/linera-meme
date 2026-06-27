use super::super::{AmsContract, AmsState};

use abi::{
    ams::{
        AmsAbi, AmsKey, AmsMessage, AmsOperation, InstantiationArgument, Metadata,
        APPLICATION_TYPES,
    },
    namespace,
    state::{StateAbi, StateOperation, StateResponse},
    store_type::StoreType,
};
use linera_sdk::{
    abi::ContractAbi,
    linera_base_types::{
        Account, AccountOwner, ApplicationId, ChainId, ChainOwnership, CryptoHash, TestString,
        Timestamp,
    },
    util::BlockingWait,
    views::View,
    Contract, ContractRuntime,
};
use serde::de::DeserializeOwned;
use std::{
    cell::RefCell,
    collections::HashMap,
    rc::Rc,
    str::FromStr,
    sync::{Arc, Mutex},
};

type RecordedStateCall = (bool, ApplicationId, StateOperation);
type StateAppRecords = Arc<Mutex<HashMap<(u8, Vec<u8>), Vec<u8>>>>;

struct TestSuite {
    ams: AmsContract,
    state_calls: Arc<Mutex<Vec<RecordedStateCall>>>,
    state_app_records: StateAppRecords,
}

impl TestSuite {
    fn new() -> Self {
        let state_calls = Arc::new(Mutex::new(Vec::new()));
        let state_calls_for_handler = state_calls.clone();
        let state_app_records = Arc::new(Mutex::new(HashMap::new()));
        let state_app_records_for_handler = state_app_records.clone();
        let runtime = ContractRuntime::new()
            .with_application_parameters(())
            .with_authenticated_signer(Self::creator_account().owner)
            .with_chain_id(Self::creator_account().chain_id)
            .with_application_creator_chain_id(Self::creator_account().chain_id)
            .with_chain_ownership(ChainOwnership::single(Self::creator_account().owner))
            .with_system_time(Timestamp::from(1))
            .with_call_application_handler(move |authenticated, application_id, call| {
                let operation = StateAbi::deserialize_operation(call).unwrap();
                state_calls_for_handler.lock().unwrap().push((
                    authenticated,
                    application_id,
                    operation.clone(),
                ));

                let response = match operation {
                    StateOperation::Read { namespace, key } => StateResponse::Read(
                        state_app_records_for_handler
                            .lock()
                            .unwrap()
                            .get(&(namespace, key))
                            .cloned(),
                    ),
                    StateOperation::Write {
                        namespace,
                        key,
                        value,
                    } => {
                        state_app_records_for_handler
                            .lock()
                            .unwrap()
                            .insert((namespace, key), value);
                        StateResponse::Ok
                    }
                    StateOperation::Delete { namespace, key } => {
                        state_app_records_for_handler
                            .lock()
                            .unwrap()
                            .remove(&(namespace, key));
                        StateResponse::Ok
                    }
                    StateOperation::BatchRead { namespace, keys } => {
                        let records = state_app_records_for_handler.lock().unwrap();
                        StateResponse::BatchRead(
                            keys.into_iter()
                                .map(|key| records.get(&(namespace, key)).cloned())
                                .collect(),
                        )
                    }
                    StateOperation::BatchWrite { namespace, writes } => {
                        let mut records = state_app_records_for_handler.lock().unwrap();
                        for (key, value) in writes {
                            records.insert((namespace, key), value);
                        }
                        StateResponse::Ok
                    }
                    StateOperation::BatchDelete { namespace, keys } => {
                        let mut records = state_app_records_for_handler.lock().unwrap();
                        for key in keys {
                            records.remove(&(namespace, key));
                        }
                        StateResponse::Ok
                    }
                    StateOperation::InitializeOperator { .. }
                    | StateOperation::CreateNamespace { .. }
                    | StateOperation::FreezeNamespace { .. }
                    | StateOperation::UnfreezeNamespace { .. }
                    | StateOperation::Handoff { .. }
                    | StateOperation::SetOperator { .. } => StateResponse::Ok,
                };
                StateAbi::serialize_response(response).unwrap()
            })
            .with_application_id(Self::ams_application_id().with_abi::<AmsAbi>());
        let mut ams = AmsContract {
            state: Rc::new(RefCell::new(
                AmsState::load(runtime.root_view_storage_context())
                    .blocking_wait()
                    .expect("Failed to read from mock key value store"),
            )),
            runtime: Rc::new(RefCell::new(runtime)),
        };

        ams.instantiate(InstantiationArgument {
            state_app_id: Self::state_application_id(),
        })
        .blocking_wait();

        let suite = Self {
            ams,
            state_calls,
            state_app_records,
        };
        assert_eq!(
            suite
                .read_state_app_record::<Vec<String>>(&AmsKey::ApplicationTypes)
                .unwrap()
                .len(),
            APPLICATION_TYPES.len()
        );
        assert_eq!(
            suite
                .ams
                .state
                .borrow()
                .state_app_id
                .get()
                .as_ref()
                .copied(),
            Some(Self::state_application_id())
        );
        suite
    }

    async fn execute_message(&mut self, message: AmsMessage) {
        self.ams.execute_message(message).await;
    }

    async fn execute_operation(&mut self, operation: AmsOperation) {
        self.ams.execute_operation(operation).await;
    }

    fn set_authenticated_account(&mut self, account: Account) {
        self.ams
            .runtime
            .borrow_mut()
            .set_authenticated_signer(Some(account.owner));
        self.ams
            .runtime
            .borrow_mut()
            .set_message_origin_chain_id(account.chain_id);
    }

    fn read_state_app_record<V: DeserializeOwned>(&self, key: &AmsKey) -> Option<V> {
        let key = Self::state_record_key(key);
        self.state_app_records
            .lock()
            .unwrap()
            .get(&key)
            .map(|value| bcs::from_bytes(value).unwrap())
    }

    fn state_calls(&self) -> Vec<RecordedStateCall> {
        self.state_calls.lock().unwrap().clone()
    }

    fn sent_messages(&self) -> Vec<(ChainId, AmsMessage)> {
        self.ams
            .runtime
            .borrow()
            .created_send_message_requests()
            .iter()
            .map(|request| (request.destination, request.message.clone()))
            .collect()
    }
    fn assert_operation_sent_message(&self, expected_message: AmsMessage) {
        let messages = self.sent_messages();
        assert_eq!(messages.len(), 1);
        assert_eq!(messages[0].0, Self::creator_account().chain_id);
        Self::assert_message_eq(&messages[0].1, &expected_message);
    }

    fn assert_message_eq(actual: &AmsMessage, expected: &AmsMessage) {
        match (actual, expected) {
            (
                AmsMessage::Register { metadata: actual },
                AmsMessage::Register { metadata: expected },
            ) => {
                assert_eq!(actual, expected);
            }
            (
                AmsMessage::Claim {
                    application_id: actual,
                },
                AmsMessage::Claim {
                    application_id: expected,
                },
            ) => {
                assert_eq!(actual, expected);
            }
            (
                AmsMessage::AddApplicationType {
                    owner: actual_owner,
                    application_type: actual_type,
                },
                AmsMessage::AddApplicationType {
                    owner: expected_owner,
                    application_type: expected_type,
                },
            ) => {
                assert_eq!(actual_owner, expected_owner);
                assert_eq!(actual_type, expected_type);
            }
            (
                AmsMessage::Update {
                    owner: actual_owner,
                    application_id: actual_id,
                    metadata: actual_metadata,
                },
                AmsMessage::Update {
                    owner: expected_owner,
                    application_id: expected_id,
                    metadata: expected_metadata,
                },
            ) => {
                assert_eq!(actual_owner, expected_owner);
                assert_eq!(actual_id, expected_id);
                assert_eq!(actual_metadata, expected_metadata);
            }
            _ => panic!("unexpected AMS message variant"),
        }
    }

    fn state_record_key(key: &AmsKey) -> (u8, Vec<u8>) {
        (namespace::AMS, bcs::to_bytes(key).unwrap())
    }

    fn metadata(application_id: ApplicationId, application_type: &str) -> Metadata {
        Metadata {
            creator: Self::creator_account(),
            application_name: "Test App".to_string(),
            application_id,
            application_type: application_type.to_string(),
            key_words: vec!["test".to_string()],
            logo_store_type: StoreType::S3,
            logo: CryptoHash::new(&TestString::new("logo".to_string())),
            description: "First description".to_string(),
            twitter: None,
            telegram: None,
            discord: None,
            website: None,
            github: None,
            spec: None,
            created_at: Timestamp::from(1),
        }
    }

    fn ams_application_id() -> ApplicationId {
        Self::application_id("b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bad")
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

    fn same_owner_different_chain_account() -> Account {
        Account {
            chain_id: ChainId::from_str(
                "abdb7c1079f36eaa03f629540283a881eb4256d1ece83a84415022d4d2a9ac65",
            )
            .unwrap(),
            owner: Self::creator_account().owner,
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

    fn state_application_id() -> ApplicationId {
        ApplicationId::from_str("b20ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bad")
            .unwrap()
    }
}

#[tokio::test(flavor = "multi_thread")]
async fn operation_register_routes_message_without_state_write() {
    let mut suite = TestSuite::new();
    let metadata = TestSuite::metadata(
        TestSuite::application_id(
            "b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bae",
        ),
        "Meme",
    );

    suite
        .execute_operation(AmsOperation::Register {
            metadata: metadata.clone(),
        })
        .await;

    let mut expected = metadata;
    expected.creator = TestSuite::creator_account();
    expected.created_at = Timestamp::from(1);
    suite.assert_operation_sent_message(AmsMessage::Register { metadata: expected });
    assert_eq!(suite.state_calls().len(), 3);
}

#[tokio::test(flavor = "multi_thread")]
async fn operation_add_application_type_routes_message_without_state_write() {
    let mut suite = TestSuite::new();

    suite
        .execute_operation(AmsOperation::AddApplicationType {
            application_type: "Analytics".to_string(),
        })
        .await;

    suite.assert_operation_sent_message(AmsMessage::AddApplicationType {
        owner: TestSuite::creator_account(),
        application_type: "Analytics".to_string(),
    });
    assert_eq!(suite.state_calls().len(), 3);
}

#[tokio::test(flavor = "multi_thread")]
async fn operation_claim_routes_message_without_state_write() {
    let mut suite = TestSuite::new();
    let application_id = TestSuite::application_id(
        "b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bae",
    );

    suite
        .execute_operation(AmsOperation::Claim { application_id })
        .await;

    suite.assert_operation_sent_message(AmsMessage::Claim { application_id });
    assert_eq!(suite.state_calls().len(), 3);
}

#[tokio::test(flavor = "multi_thread")]
async fn operation_update_routes_message_without_state_write() {
    let mut suite = TestSuite::new();
    let application_id = TestSuite::application_id(
        "b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bae",
    );
    let metadata = TestSuite::metadata(application_id, "Meme");

    suite
        .execute_operation(AmsOperation::Update {
            application_id,
            metadata: metadata.clone(),
        })
        .await;

    suite.assert_operation_sent_message(AmsMessage::Update {
        owner: TestSuite::creator_account(),
        application_id,
        metadata,
    });
    assert_eq!(suite.state_calls().len(), 3);
}

#[tokio::test(flavor = "multi_thread")]
async fn message_register_application_success() {
    let mut suite = TestSuite::new();
    let metadata = TestSuite::metadata(
        TestSuite::application_id(
            "b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bae",
        ),
        "Meme",
    );

    suite
        .execute_message(AmsMessage::Register {
            metadata: metadata.clone(),
        })
        .await;

    assert_eq!(
        suite
            .read_state_app_record::<Metadata>(&AmsKey::Application {
                application_id: metadata.application_id,
            })
            .unwrap(),
        metadata
    );
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic(expected = "Already exists")]
async fn message_register_application_rejects_duplicate_application_id() {
    let mut suite = TestSuite::new();
    let metadata = TestSuite::metadata(
        TestSuite::application_id(
            "b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bae",
        ),
        "Meme",
    );

    suite
        .execute_message(AmsMessage::Register {
            metadata: metadata.clone(),
        })
        .await;
    suite
        .execute_message(AmsMessage::Register { metadata })
        .await;
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic(expected = "Invalid application type")]
async fn message_register_application_rejects_unknown_application_type() {
    let mut suite = TestSuite::new();
    let metadata = TestSuite::metadata(
        TestSuite::application_id(
            "b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bae",
        ),
        "UnknownType",
    );

    suite
        .execute_message(AmsMessage::Register { metadata })
        .await;
}

#[tokio::test(flavor = "multi_thread")]
async fn message_add_application_type_success() {
    let mut suite = TestSuite::new();

    suite
        .execute_message(AmsMessage::AddApplicationType {
            owner: TestSuite::creator_account(),
            application_type: "Analytics".to_string(),
        })
        .await;

    let application_types = suite
        .read_state_app_record::<Vec<String>>(&AmsKey::ApplicationTypes)
        .unwrap();
    assert!(application_types.contains(&"Analytics".to_string()));
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic(expected = "Permission denied")]
async fn message_add_application_type_rejects_non_operator() {
    let mut suite = TestSuite::new();

    suite
        .execute_message(AmsMessage::AddApplicationType {
            owner: TestSuite::other_account(),
            application_type: "Analytics".to_string(),
        })
        .await;
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic(expected = "Already exists")]
async fn message_add_application_type_rejects_duplicate_type() {
    let mut suite = TestSuite::new();

    suite
        .execute_message(AmsMessage::AddApplicationType {
            owner: TestSuite::creator_account(),
            application_type: "Analytics".to_string(),
        })
        .await;
    suite
        .execute_message(AmsMessage::AddApplicationType {
            owner: TestSuite::creator_account(),
            application_type: "Analytics".to_string(),
        })
        .await;
}

#[tokio::test(flavor = "multi_thread")]
async fn message_claim_application_success_for_same_owner() {
    let mut suite = TestSuite::new();
    suite.set_authenticated_account(TestSuite::same_owner_different_chain_account());
    let application_id = TestSuite::application_id(
        "b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bae",
    );
    let metadata = TestSuite::metadata(application_id, "Meme");

    suite
        .execute_message(AmsMessage::Register { metadata })
        .await;
    suite
        .execute_message(AmsMessage::Claim { application_id })
        .await;

    let stored = suite
        .read_state_app_record::<Metadata>(&AmsKey::Application { application_id })
        .unwrap();
    assert_eq!(
        stored.creator,
        TestSuite::same_owner_different_chain_account()
    );
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic(expected = "Not exists")]
async fn message_claim_application_rejects_unknown_application() {
    let mut suite = TestSuite::new();
    suite.set_authenticated_account(TestSuite::same_owner_different_chain_account());

    suite
        .execute_message(AmsMessage::Claim {
            application_id: TestSuite::application_id(
                "b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bae",
            ),
        })
        .await;
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic(expected = "Permission denied")]
async fn message_claim_application_rejects_different_owner() {
    let mut suite = TestSuite::new();
    let application_id = TestSuite::application_id(
        "b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bae",
    );
    let metadata = TestSuite::metadata(application_id, "Meme");

    suite
        .execute_message(AmsMessage::Register { metadata })
        .await;
    suite.set_authenticated_account(TestSuite::other_account());
    suite
        .execute_message(AmsMessage::Claim { application_id })
        .await;
}

#[tokio::test(flavor = "multi_thread")]
async fn message_update_application_success() {
    let mut suite = TestSuite::new();
    let application_id = TestSuite::application_id(
        "b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bae",
    );
    let metadata = TestSuite::metadata(application_id, "Meme");
    let mut updated = metadata.clone();
    updated.application_name = "Updated App".to_string();
    updated.description = "Updated description".to_string();
    updated.application_type = "Game".to_string();
    updated.key_words = vec!["updated".to_string()];
    updated.spec = Some("{\"k\":\"v\"}".to_string());

    suite
        .execute_message(AmsMessage::Register { metadata })
        .await;
    suite
        .execute_message(AmsMessage::Update {
            owner: TestSuite::creator_account(),
            application_id,
            metadata: updated,
        })
        .await;

    let stored = suite
        .read_state_app_record::<Metadata>(&AmsKey::Application { application_id })
        .unwrap();
    assert_eq!(stored.application_name, "Updated App");
    assert_eq!(stored.description, "Updated description");
    assert_eq!(stored.application_type, "Game");
    assert_eq!(stored.key_words, vec!["updated".to_string()]);
    assert_eq!(stored.spec, Some("{\"k\":\"v\"}".to_string()));
    assert_eq!(stored.creator, TestSuite::creator_account());
    assert_eq!(stored.created_at, Timestamp::from(1));
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic(expected = "Permission denied")]
async fn message_update_application_rejects_different_owner() {
    let mut suite = TestSuite::new();
    let application_id = TestSuite::application_id(
        "b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bae",
    );
    let metadata = TestSuite::metadata(application_id, "Meme");

    suite
        .execute_message(AmsMessage::Register {
            metadata: metadata.clone(),
        })
        .await;
    suite
        .execute_message(AmsMessage::Update {
            owner: TestSuite::other_account(),
            application_id,
            metadata,
        })
        .await;
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic(expected = "Invalid application type")]
async fn message_update_application_rejects_unknown_application_type() {
    let mut suite = TestSuite::new();
    let application_id = TestSuite::application_id(
        "b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bae",
    );
    let metadata = TestSuite::metadata(application_id, "Meme");
    let mut updated = metadata.clone();
    updated.application_type = "UnknownType".to_string();

    suite
        .execute_message(AmsMessage::Register { metadata })
        .await;
    suite
        .execute_message(AmsMessage::Update {
            owner: TestSuite::creator_account(),
            application_id,
            metadata: updated,
        })
        .await;
}

#[test]
fn instantiate_initializes_state_app_records() {
    let suite = TestSuite::new();
    let calls = suite.state_calls();
    let expected_application_types = APPLICATION_TYPES
        .iter()
        .map(|application_type| application_type.to_string())
        .collect::<Vec<_>>();

    assert_eq!(calls.len(), 3);
    assert!(calls
        .iter()
        .all(|(authenticated, application_id, _operation)| {
            *authenticated && *application_id == TestSuite::state_application_id()
        }));
    assert_eq!(
        calls[0].2,
        StateOperation::InitializeOperator {
            operator: TestSuite::creator_account()
        }
    );
    assert_eq!(
        calls[1].2,
        StateOperation::CreateNamespace {
            namespace: namespace::AMS
        }
    );
    assert_eq!(
        calls[2].2,
        StateOperation::BatchWrite {
            namespace: namespace::AMS,
            writes: vec![
                (
                    bcs::to_bytes(&AmsKey::Operator).unwrap(),
                    bcs::to_bytes(&TestSuite::creator_account()).unwrap(),
                ),
                (
                    bcs::to_bytes(&AmsKey::ApplicationTypes).unwrap(),
                    bcs::to_bytes(&expected_application_types).unwrap(),
                ),
                (
                    bcs::to_bytes(&AmsKey::ApplicationIds).unwrap(),
                    bcs::to_bytes(&Vec::<ApplicationId>::new()).unwrap(),
                ),
            ],
        }
    );
}

#[test]
fn ams_key_encoding_is_stable_for_state_app_records() {
    let key = abi::ams::AmsKey::Application {
        application_id: TestSuite::application_id(
            "b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bae",
        ),
    };

    assert_eq!(
        bcs::to_bytes(&key).unwrap(),
        vec![
            1, 177, 10, 193, 28, 53, 105, 217, 225, 182, 226, 47, 229, 15, 140, 29, 232, 179, 58,
            1, 23, 59, 69, 99, 198, 20, 170, 7, 216, 184, 235, 91, 174,
        ]
    );
}
