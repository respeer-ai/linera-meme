use super::super::{AmsContract, AmsState};

use abi::{
    ams::{AmsAbi, AmsKey, AmsMessage, InstantiationArgument, Metadata, APPLICATION_TYPES},
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
use std::str::FromStr;
use std::{
    cell::RefCell,
    rc::Rc,
    sync::{Arc, Mutex},
};

type RecordedStateCall = (bool, ApplicationId, StateOperation);

#[tokio::test(flavor = "multi_thread")]
async fn message_register_application_success() {
    let mut ams = create_and_instantiate_ams();
    let metadata = test_metadata(
        creator_account(),
        application_id("b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bae"),
        "Meme",
        "Test App",
        "First description",
    );

    ams.execute_message(AmsMessage::Register {
        metadata: metadata.clone(),
    })
    .await;

    assert_eq!(
        ams.state
            .borrow()
            .applications
            .get(&metadata.application_id)
            .await
            .unwrap()
            .unwrap(),
        metadata
    );
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic(expected = "Already exists")]
async fn message_register_application_rejects_duplicate_application_id() {
    let mut ams = create_and_instantiate_ams();
    let metadata = test_metadata(
        creator_account(),
        application_id("b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bae"),
        "Meme",
        "Test App",
        "First description",
    );

    ams.execute_message(AmsMessage::Register {
        metadata: metadata.clone(),
    })
    .await;
    ams.execute_message(AmsMessage::Register { metadata }).await;
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic(expected = "Invalid application type")]
async fn message_register_application_rejects_unknown_application_type() {
    let mut ams = create_and_instantiate_ams();
    let metadata = test_metadata(
        creator_account(),
        application_id("b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bae"),
        "UnknownType",
        "Test App",
        "First description",
    );

    ams.execute_message(AmsMessage::Register { metadata }).await;
}

#[tokio::test(flavor = "multi_thread")]
async fn message_add_application_type_success() {
    let mut ams = create_and_instantiate_ams();
    let owner = creator_account();

    ams.execute_message(AmsMessage::AddApplicationType {
        owner,
        application_type: "Analytics".to_string(),
    })
    .await;

    assert_eq!(
        ams.state
            .borrow()
            .application_types
            .elements()
            .await
            .unwrap()
            .contains(&"Analytics".to_string()),
        true
    );
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic(expected = "Permission denied")]
async fn message_add_application_type_rejects_non_operator() {
    let mut ams = create_and_instantiate_ams();

    ams.execute_message(AmsMessage::AddApplicationType {
        owner: other_account(),
        application_type: "Analytics".to_string(),
    })
    .await;
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic(expected = "Already exists")]
async fn message_add_application_type_rejects_duplicate_type() {
    let mut ams = create_and_instantiate_ams();
    let owner = creator_account();

    ams.execute_message(AmsMessage::AddApplicationType {
        owner,
        application_type: "Analytics".to_string(),
    })
    .await;
    ams.execute_message(AmsMessage::AddApplicationType {
        owner,
        application_type: "Analytics".to_string(),
    })
    .await;
}

#[tokio::test(flavor = "multi_thread")]
async fn message_claim_application_success_for_same_owner() {
    let mut ams = create_and_instantiate_ams();
    ams.runtime
        .borrow_mut()
        .set_message_origin_chain_id(same_owner_different_chain_account().chain_id);
    let application_id =
        application_id("b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bae");
    let metadata = test_metadata(
        creator_account(),
        application_id,
        "Meme",
        "Test App",
        "First description",
    );
    let claimed_account = same_owner_different_chain_account();

    ams.execute_message(AmsMessage::Register { metadata }).await;
    ams.execute_message(AmsMessage::Claim { application_id })
        .await;

    assert_eq!(
        ams.state
            .borrow()
            .applications
            .get(&application_id)
            .await
            .unwrap()
            .unwrap()
            .creator,
        claimed_account
    );
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic(expected = "Not exists")]
async fn message_claim_application_rejects_unknown_application() {
    let mut ams = create_and_instantiate_ams();
    ams.runtime
        .borrow_mut()
        .set_message_origin_chain_id(same_owner_different_chain_account().chain_id);

    ams.execute_message(AmsMessage::Claim {
        application_id: application_id(
            "b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bae",
        ),
    })
    .await;
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic(expected = "Permission denied")]
async fn message_claim_application_rejects_different_owner() {
    let mut ams = create_and_instantiate_ams();
    ams.runtime
        .borrow_mut()
        .set_authenticated_signer(Some(other_account().owner));
    ams.runtime
        .borrow_mut()
        .set_message_origin_chain_id(other_account().chain_id);
    let application_id =
        application_id("b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bae");
    let metadata = test_metadata(
        creator_account(),
        application_id,
        "Meme",
        "Test App",
        "First description",
    );

    ams.execute_message(AmsMessage::Register { metadata }).await;
    ams.execute_message(AmsMessage::Claim { application_id })
        .await;
}

#[tokio::test(flavor = "multi_thread")]
async fn message_update_application_success() {
    let mut ams = create_and_instantiate_ams();
    let application_id =
        application_id("b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bae");
    let metadata = test_metadata(
        creator_account(),
        application_id,
        "Meme",
        "Test App",
        "First description",
    );
    let mut updated = metadata.clone();
    updated.application_name = "Updated App".to_string();
    updated.description = "Updated description".to_string();
    updated.application_type = "Game".to_string();
    updated.key_words = vec!["updated".to_string()];
    updated.spec = Some("{\"k\":\"v\"}".to_string());

    ams.execute_message(AmsMessage::Register { metadata }).await;
    ams.execute_message(AmsMessage::Update {
        owner: creator_account(),
        application_id,
        metadata: updated,
    })
    .await;

    let stored = ams
        .state
        .borrow()
        .applications
        .get(&application_id)
        .await
        .unwrap()
        .unwrap();
    assert_eq!(stored.application_name, "Updated App");
    assert_eq!(stored.description, "Updated description");
    assert_eq!(stored.application_type, "Game");
    assert_eq!(stored.key_words, vec!["updated".to_string()]);
    assert_eq!(stored.spec, Some("{\"k\":\"v\"}".to_string()));
    assert_eq!(stored.creator, creator_account());
    assert_eq!(stored.created_at, Timestamp::from(1));
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic(expected = "Permission denied")]
async fn message_update_application_rejects_different_owner() {
    let mut ams = create_and_instantiate_ams();
    let application_id =
        application_id("b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bae");
    let metadata = test_metadata(
        creator_account(),
        application_id,
        "Meme",
        "Test App",
        "First description",
    );

    ams.execute_message(AmsMessage::Register {
        metadata: metadata.clone(),
    })
    .await;
    ams.execute_message(AmsMessage::Update {
        owner: other_account(),
        application_id,
        metadata,
    })
    .await;
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic(expected = "Invalid application type")]
async fn message_update_application_rejects_unknown_application_type() {
    let mut ams = create_and_instantiate_ams();
    let application_id =
        application_id("b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bae");
    let metadata = test_metadata(
        creator_account(),
        application_id,
        "Meme",
        "Test App",
        "First description",
    );
    let mut updated = metadata.clone();
    updated.application_type = "UnknownType".to_string();

    ams.execute_message(AmsMessage::Register { metadata }).await;
    ams.execute_message(AmsMessage::Update {
        owner: creator_account(),
        application_id,
        metadata: updated,
    })
    .await;
}

#[test]
fn instantiate_initializes_state_app_records() {
    let (_ams, calls) = create_and_instantiate_ams_recording_state_calls();
    let calls = calls.lock().unwrap();
    let expected_application_types = APPLICATION_TYPES
        .iter()
        .map(|application_type| application_type.to_string())
        .collect::<Vec<_>>();

    assert_eq!(calls.len(), 4);
    assert!(calls
        .iter()
        .all(|(authenticated, application_id, _operation)| {
            *authenticated && *application_id == state_application_id()
        }));
    assert_eq!(
        calls[0].2,
        StateOperation::InitializeOperator {
            operator: creator_account()
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
        StateOperation::Write {
            namespace: namespace::AMS,
            key: bcs::to_bytes(&AmsKey::Operator).unwrap(),
            value: bcs::to_bytes(&creator_account()).unwrap(),
        }
    );
    assert_eq!(
        calls[3].2,
        StateOperation::Write {
            namespace: namespace::AMS,
            key: bcs::to_bytes(&AmsKey::ApplicationTypes).unwrap(),
            value: bcs::to_bytes(&expected_application_types).unwrap(),
        }
    );
}

fn create_and_instantiate_ams() -> AmsContract {
    create_and_instantiate_ams_recording_state_calls().0
}

fn create_and_instantiate_ams_recording_state_calls(
) -> (AmsContract, Arc<Mutex<Vec<RecordedStateCall>>>) {
    let chain_id =
        ChainId::from_str("aee928d4bf3880353b4a3cd9b6f88e6cc6e5ed050860abae439e7782e9b2dfe8")
            .unwrap();
    let owner = AccountOwner::from_str(
        "0x02e900512d2fca22897f80a2f6932ff454f2752ef7afad18729dd25e5b5b6e00",
    )
    .unwrap();
    let application_id =
        ApplicationId::from_str("b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bad")
            .unwrap()
            .with_abi::<AmsAbi>();
    let state_calls = Arc::new(Mutex::new(Vec::new()));
    let state_calls_for_handler = state_calls.clone();
    let runtime = ContractRuntime::new()
        .with_application_parameters(())
        .with_authenticated_signer(owner)
        .with_chain_id(chain_id)
        .with_application_creator_chain_id(chain_id)
        .with_chain_ownership(ChainOwnership::single(owner))
        .with_system_time(Timestamp::from(1))
        .with_call_application_handler(move |authenticated, application_id, call| {
            let operation = StateAbi::deserialize_operation(call).unwrap();
            state_calls_for_handler.lock().unwrap().push((
                authenticated,
                application_id,
                operation,
            ));
            StateAbi::serialize_response(StateResponse::Ok).unwrap()
        })
        .with_application_id(application_id);
    let mut contract = AmsContract {
        state: Rc::new(RefCell::new(
            AmsState::load(runtime.root_view_storage_context())
                .blocking_wait()
                .expect("Failed to read from mock key value store"),
        )),
        runtime: Rc::new(RefCell::new(runtime)),
    };

    contract
        .instantiate(InstantiationArgument {
            state_app_id: state_application_id(),
        })
        .blocking_wait();

    assert_eq!(
        contract
            .state
            .borrow()
            .application_types
            .elements()
            .blocking_wait()
            .unwrap()
            .len(),
        APPLICATION_TYPES.len()
    );

    assert_eq!(
        contract.state.borrow().state_app_id.get().as_ref().copied(),
        Some(state_application_id())
    );
    (contract, state_calls)
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
        owner: creator_account().owner,
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

fn application_id(value: &str) -> ApplicationId {
    ApplicationId::from_str(value).unwrap()
}

fn test_metadata(
    creator: Account,
    application_id: ApplicationId,
    application_type: &str,
    application_name: &str,
    description: &str,
) -> Metadata {
    Metadata {
        creator,
        application_name: application_name.to_string(),
        application_id,
        application_type: application_type.to_string(),
        key_words: vec!["test".to_string()],
        logo_store_type: StoreType::S3,
        logo: CryptoHash::new(&TestString::new("logo".to_string())),
        description: description.to_string(),
        twitter: None,
        telegram: None,
        discord: None,
        website: None,
        github: None,
        spec: None,
        created_at: Timestamp::from(1),
    }
}

#[test]
fn ams_key_encoding_is_stable_for_state_app_records() {
    let key = abi::ams::AmsKey::Application {
        application_id: application_id(
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

fn state_application_id() -> ApplicationId {
    ApplicationId::from_str("b20ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bad")
        .unwrap()
}
