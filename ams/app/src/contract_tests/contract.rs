use super::super::{AmsContract, AmsState};

use abi::{
    ams::{
        abi::{AmsAbi, AmsMessage, AmsOperation, InstantiationArgument, Metadata},
        state_v1::{
            AmsStateAbi as AmsStateV1Abi, AmsStateOperation as AmsStateV1Operation,
            AmsStateResponse as AmsStateV1Response,
        },
    },
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
use std::{cell::RefCell, rc::Rc, str::FromStr};

struct TestSuite {
    ams: AmsContract,
}

impl TestSuite {
    fn new() -> Self {
        let runtime = ContractRuntime::new()
            .with_application_parameters(())
            .with_authenticated_signer(Self::creator_account().owner)
            .with_chain_id(Self::creator_account().chain_id)
            .with_application_creator_chain_id(Self::creator_account().chain_id)
            .with_chain_ownership(ChainOwnership::single(Self::creator_account().owner))
            .with_system_time(Timestamp::from(1))
            .with_application_id(Self::ams_application_id().with_abi::<AmsAbi>());
        let mut ams = AmsContract {
            state: Rc::new(RefCell::new(
                AmsState::load(runtime.root_view_storage_context())
                    .blocking_wait()
                    .expect("Failed to read from mock key value store"),
            )),
            runtime: Rc::new(RefCell::new(runtime)),
        };

        ams.instantiate(InstantiationArgument {}).blocking_wait();

        let suite = Self { ams };
        assert_eq!(suite.ams.state.borrow().latest_state_version.get(), &0);
        suite
    }

    async fn execute_message(&mut self, message: AmsMessage) {
        self.ams.execute_message(message).await;
    }

    async fn execute_operation(&mut self, operation: AmsOperation) {
        self.ams.execute_operation(operation).await;
    }

    async fn append_state(&mut self) {
        self.execute_operation(AmsOperation::AppendState {
            state_application_id: Self::state_application_id(),
        })
        .await;
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
async fn operation_append_state_records_state_v1_application() {
    let mut suite = TestSuite::new();

    suite
        .execute_operation(AmsOperation::AppendState {
            state_application_id: TestSuite::state_application_id(),
        })
        .await;

    assert_eq!(suite.ams.state.borrow().latest_state_version.get(), &1);
    assert_eq!(
        suite
            .ams
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
        .ams
        .runtime
        .borrow_mut()
        .set_chain_id(TestSuite::other_account().chain_id);

    suite
        .execute_operation(AmsOperation::AppendState {
            state_application_id: TestSuite::state_application_id(),
        })
        .await;
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic(expected = "Invalid state version")]
async fn operation_append_state_rejects_second_state_version_for_state_v1_app() {
    let mut suite = TestSuite::new();
    suite.append_state().await;

    suite
        .execute_operation(AmsOperation::AppendState {
            state_application_id: TestSuite::application_id(
                "b60ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bae",
            ),
        })
        .await;
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic(expected = "Already exists")]
async fn operation_append_state_rejects_duplicate_state_application_id() {
    let mut suite = TestSuite::new();
    suite.append_state().await;

    suite
        .execute_operation(AmsOperation::AppendState {
            state_application_id: TestSuite::state_application_id(),
        })
        .await;
}

#[tokio::test(flavor = "multi_thread")]
async fn operation_set_operator_calls_state_v1_set_operator() {
    let mut suite = TestSuite::new();
    suite.append_state().await;
    let new_operator = TestSuite::other_account();

    suite.ams.runtime.borrow_mut().set_call_application_handler(
        move |authenticated, application_id, call| {
            assert!(authenticated);
            assert_eq!(application_id, TestSuite::state_application_id());
            assert_eq!(
                AmsStateV1Abi::deserialize_operation(call).unwrap(),
                AmsStateV1Operation::SetOperator { new_operator }
            );
            AmsStateV1Abi::serialize_response(AmsStateV1Response::Ok).unwrap()
        },
    );

    suite
        .execute_operation(AmsOperation::SetOperator { new_operator })
        .await;
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic(expected = "Invalid state version")]
async fn operation_set_operator_rejects_missing_state_v1_append() {
    let mut suite = TestSuite::new();
    let new_operator = TestSuite::other_account();

    suite
        .execute_operation(AmsOperation::SetOperator { new_operator })
        .await;
}

#[tokio::test(flavor = "multi_thread")]
async fn operation_handoff_calls_state_v1_handoff() {
    let mut suite = TestSuite::new();
    suite.append_state().await;
    let new_business_application_id = TestSuite::application_id(
        "b70ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bae",
    );

    suite.ams.runtime.borrow_mut().set_call_application_handler(
        move |authenticated, application_id, call| {
            assert!(authenticated);
            assert_eq!(application_id, TestSuite::state_application_id());
            assert_eq!(
                AmsStateV1Abi::deserialize_operation(call).unwrap(),
                AmsStateV1Operation::Handoff {
                    new_business_application_id,
                }
            );
            AmsStateV1Abi::serialize_response(AmsStateV1Response::Ok).unwrap()
        },
    );

    suite
        .execute_operation(AmsOperation::Handoff {
            new_business_application_id,
        })
        .await;
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic(expected = "Invalid state version")]
async fn operation_handoff_rejects_missing_state_v1_append() {
    let mut suite = TestSuite::new();
    let new_business_application_id = TestSuite::application_id(
        "b70ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bae",
    );

    suite
        .execute_operation(AmsOperation::Handoff {
            new_business_application_id,
        })
        .await;
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
}

#[tokio::test(flavor = "multi_thread")]
async fn message_register_application_calls_state_v1_register() {
    let mut suite = TestSuite::new();
    suite.append_state().await;
    let metadata = TestSuite::metadata(
        TestSuite::application_id(
            "b30ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bae",
        ),
        "UnknownType",
    );

    let expected_metadata = metadata.clone();
    suite.ams.runtime.borrow_mut().set_call_application_handler(
        move |authenticated, application_id, call| {
            assert!(authenticated);
            assert_eq!(application_id, TestSuite::state_application_id());
            assert_eq!(
                AmsStateV1Abi::deserialize_operation(call).unwrap(),
                AmsStateV1Operation::RegisterApplication {
                    metadata: expected_metadata.clone(),
                }
            );
            AmsStateV1Abi::serialize_response(AmsStateV1Response::Ok).unwrap()
        },
    );

    suite
        .execute_message(AmsMessage::Register {
            metadata: metadata.clone(),
        })
        .await;
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic(expected = "Not exists")]
async fn message_register_application_rejects_missing_state_v1_append() {
    let mut suite = TestSuite::new();
    let metadata = TestSuite::metadata(
        TestSuite::application_id(
            "b50ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bae",
        ),
        "Meme",
    );

    suite
        .execute_message(AmsMessage::Register { metadata })
        .await;
}

#[tokio::test(flavor = "multi_thread")]
async fn message_add_application_type_success() {
    let mut suite = TestSuite::new();
    suite.append_state().await;

    suite.ams.runtime.borrow_mut().set_call_application_handler(
        move |authenticated, application_id, call| {
            assert!(authenticated);
            assert_eq!(application_id, TestSuite::state_application_id());
            assert_eq!(
                AmsStateV1Abi::deserialize_operation(call).unwrap(),
                AmsStateV1Operation::AddApplicationType {
                    owner: TestSuite::creator_account(),
                    application_type: "Analytics".to_string(),
                }
            );
            AmsStateV1Abi::serialize_response(AmsStateV1Response::Ok).unwrap()
        },
    );

    suite
        .execute_message(AmsMessage::AddApplicationType {
            owner: TestSuite::creator_account(),
            application_type: "Analytics".to_string(),
        })
        .await;
}

#[tokio::test(flavor = "multi_thread")]
async fn message_claim_application_calls_state_v1_claim_with_message_signer_account() {
    let mut suite = TestSuite::new();
    suite.append_state().await;
    suite.set_authenticated_account(TestSuite::same_owner_different_chain_account());
    let application_id = TestSuite::application_id(
        "b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bae",
    );

    suite.ams.runtime.borrow_mut().set_call_application_handler(
        move |authenticated, state_application_id, call| {
            assert!(authenticated);
            assert_eq!(state_application_id, TestSuite::state_application_id());
            assert_eq!(
                AmsStateV1Abi::deserialize_operation(call).unwrap(),
                AmsStateV1Operation::ClaimApplication {
                    owner: TestSuite::same_owner_different_chain_account(),
                    application_id,
                }
            );
            AmsStateV1Abi::serialize_response(AmsStateV1Response::Ok).unwrap()
        },
    );

    suite
        .execute_message(AmsMessage::Claim { application_id })
        .await;
}

#[tokio::test(flavor = "multi_thread")]
async fn message_update_application_calls_state_v1_update() {
    let mut suite = TestSuite::new();
    suite.append_state().await;
    let application_id = TestSuite::application_id(
        "b40ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bae",
    );
    let metadata = TestSuite::metadata(application_id, "Meme");
    let mut updated = metadata.clone();
    updated.application_type = "UnknownType".to_string();

    let expected_metadata = updated.clone();
    suite.ams.runtime.borrow_mut().set_call_application_handler(
        move |authenticated, state_application_id, call| {
            assert!(authenticated);
            assert_eq!(state_application_id, TestSuite::state_application_id());
            assert_eq!(
                AmsStateV1Abi::deserialize_operation(call).unwrap(),
                AmsStateV1Operation::UpdateApplication {
                    owner: TestSuite::other_account(),
                    application_id,
                    metadata: expected_metadata.clone(),
                }
            );
            AmsStateV1Abi::serialize_response(AmsStateV1Response::Ok).unwrap()
        },
    );

    suite
        .execute_message(AmsMessage::Update {
            owner: TestSuite::other_account(),
            application_id,
            metadata: updated.clone(),
        })
        .await;
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic(expected = "Not exists")]
async fn message_add_application_type_rejects_missing_state_v1_append() {
    let mut suite = TestSuite::new();

    suite
        .execute_message(AmsMessage::AddApplicationType {
            owner: TestSuite::creator_account(),
            application_type: "Analytics".to_string(),
        })
        .await;
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic(expected = "Not exists")]
async fn message_claim_application_rejects_missing_state_v1_append() {
    let mut suite = TestSuite::new();
    suite.set_authenticated_account(TestSuite::creator_account());
    let application_id = TestSuite::application_id(
        "b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bae",
    );

    suite
        .execute_message(AmsMessage::Claim { application_id })
        .await;
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic(expected = "Not exists")]
async fn message_update_application_rejects_missing_state_v1_append() {
    let mut suite = TestSuite::new();
    let application_id = TestSuite::application_id(
        "b40ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bae",
    );
    let metadata = TestSuite::metadata(application_id, "Meme");

    suite
        .execute_message(AmsMessage::Update {
            owner: TestSuite::other_account(),
            application_id,
            metadata,
        })
        .await;
}
