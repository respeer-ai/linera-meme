use super::super::{ProxyContract, ProxyState as BusinessState};

use abi::meme::{
    InstantiationArgument as MemeInstantiationArgument, Meme, MemeOperation, MemeParameters,
    MemeResponse, Metadata, StateInstantiationArgument as MemeStateInstantiationArgument,
};
use abi::proxy::{
    state_v1::{ProxyStateV1Operation, ProxyStateV1Response, StateInstantiationArgument},
    InitializeArgument, InstantiationArgument, ProxyAbi, ProxyMessage, ProxyOperation,
    ProxyResponse, StateBytecodeId,
};
use abi::store_type::StoreType;
use futures::FutureExt as _;
use linera_sdk::{
    bcs,
    linera_base_types::{
        Account, AccountOwner, ApplicationId, ApplicationPermissions, ChainId, ChainOwnership,
        ModuleId, Timestamp,
    },
    util::BlockingWait,
    views::View,
    Contract, ContractRuntime,
};
use proxy_state::{interfaces::state::StateInterface, state::ProxyState as StateAppState};
use std::str::FromStr;
use std::{cell::RefCell, rc::Rc};

#[test]
#[should_panic(expected = "Failed: construct operation handler: NotAllowed")]
fn op_propose_add_genesis_miner() {
    let _ = env_logger::builder().is_test(true).try_init();
    let (mut proxy, _state) = create_and_instantiate_proxy();

    let owner = AccountOwner::from_str(
        "0x02e900512d2fca22897f80a2f6932ff454f2752ef7afad18729dd25e5b5b6e01",
    )
    .unwrap();
    let chain_id =
        ChainId::from_str("aee928d4bf3880353b4a3cd9b6f88e6cc6e5ed050860abae439e7782e9b2dfe8")
            .unwrap();
    let owner = Account { chain_id, owner };

    let response = proxy
        .execute_operation(ProxyOperation::ProposeAddGenesisMiner { owner })
        .now_or_never()
        .expect("Execution of proxy operation should not await anything");

    assert!(matches!(response, ProxyResponse::Ok));
}

#[tokio::test(flavor = "multi_thread")]
async fn msg_propose_add_genesis_miner() {
    let _ = env_logger::builder().is_test(true).try_init();
    let (mut proxy, state) = create_and_instantiate_proxy();

    let owner = AccountOwner::from_str(
        "0x02e900512d2fca22897f80a2f6932ff454f2752ef7afad18729dd25e5b5b6e00",
    )
    .unwrap();
    let chain_id =
        ChainId::from_str("aee928d4bf3880353b4a3cd9b6f88e6cc6e5ed050860abae439e7782e9b2dfe8")
            .unwrap();
    let operator = Account { chain_id, owner };
    let owner = AccountOwner::from_str(
        "0x02e900512d2fca22897f80a2f6932ff454f2752ef7afad18729dd25e5b5b6e01",
    )
    .unwrap();
    let owner = Account { chain_id, owner };

    proxy
        .execute_message(ProxyMessage::ProposeAddGenesisMiner { operator, owner })
        .await;

    assert_eq!(
        state.borrow().is_genesis_miner(owner).blocking_wait().unwrap(),
        true
    );
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic(expected = "Already registered")]
async fn msg_register_miner_rejects_duplicate_owner_on_different_chain() {
    let (mut proxy, _state) = create_and_instantiate_proxy();
    let owner = AccountOwner::from_str(
        "0x02e900512d2fca22897f80a2f6932ff454f2752ef7afad18729dd25e5b5b6e09",
    )
    .unwrap();
    let chain_id =
        ChainId::from_str("aee928d4bf3880353b4a3cd9b6f88e6cc6e5ed050860abae439e7782e9b2dfe8")
            .unwrap();
    let other_chain_id =
        ChainId::from_str("abdb7c1079f36eaa03f629540283a881eb4256d1ece83a84415022d4d2a9ac65")
            .unwrap();
    let registered = Account { chain_id, owner };
    let duplicate = Account {
        chain_id: other_chain_id,
        owner,
    };

    proxy
        .execute_message(ProxyMessage::RegisterMiner { owner: registered })
        .await;
    proxy
        .execute_message(ProxyMessage::RegisterMiner { owner: duplicate })
        .await;
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic(expected = "Invalid state response")]
async fn msg_deregister_miner_rejects_unregistered_owner() {
    let (mut proxy, _state) = create_and_instantiate_proxy();
    let owner = AccountOwner::from_str(
        "0x02e900512d2fca22897f80a2f6932ff454f2752ef7afad18729dd25e5b5b6e10",
    )
    .unwrap();
    let chain_id =
        ChainId::from_str("aee928d4bf3880353b4a3cd9b6f88e6cc6e5ed050860abae439e7782e9b2dfe8")
            .unwrap();

    proxy
        .execute_message(ProxyMessage::DeregisterMiner {
            owner: Account { chain_id, owner },
        })
        .await;
}

#[tokio::test(flavor = "multi_thread")]
async fn msg_deregister_miner_rejects_wrong_chain_for_registered_owner() {
    let (mut proxy, state) = create_and_instantiate_proxy();
    let owner = AccountOwner::from_str(
        "0x02e900512d2fca22897f80a2f6932ff454f2752ef7afad18729dd25e5b5b6e11",
    )
    .unwrap();
    let chain_id =
        ChainId::from_str("aee928d4bf3880353b4a3cd9b6f88e6cc6e5ed050860abae439e7782e9b2dfe8")
            .unwrap();
    let other_chain_id =
        ChainId::from_str("abdb7c1079f36eaa03f629540283a881eb4256d1ece83a84415022d4d2a9ac65")
            .unwrap();
    let registered = Account { chain_id, owner };
    let wrong_chain = Account {
        chain_id: other_chain_id,
        owner,
    };

    proxy
        .execute_message(ProxyMessage::RegisterMiner { owner: registered })
        .await;

    let result = std::panic::AssertUnwindSafe(async {
        proxy
            .execute_message(ProxyMessage::DeregisterMiner { owner: wrong_chain })
            .await;
    })
    .catch_unwind()
    .await;

    assert!(result.is_err());
    assert_eq!(
        state
            .borrow()
            .miners
            .contains_key(&registered)
            .blocking_wait()
            .unwrap(),
        true
    );
}

#[tokio::test(flavor = "multi_thread")]
async fn msg_deregister_miner_rejects_other_owner_without_touching_registered_miner() {
    let (mut proxy, state) = create_and_instantiate_proxy();
    let chain_id =
        ChainId::from_str("aee928d4bf3880353b4a3cd9b6f88e6cc6e5ed050860abae439e7782e9b2dfe8")
            .unwrap();
    let registered = Account {
        chain_id,
        owner: AccountOwner::from_str(
            "0x02e900512d2fca22897f80a2f6932ff454f2752ef7afad18729dd25e5b5b6e12",
        )
        .unwrap(),
    };
    let other_owner = Account {
        chain_id,
        owner: AccountOwner::from_str(
            "0x02e900512d2fca22897f80a2f6932ff454f2752ef7afad18729dd25e5b5b6e13",
        )
        .unwrap(),
    };

    proxy
        .execute_message(ProxyMessage::RegisterMiner { owner: registered })
        .await;

    let result = std::panic::AssertUnwindSafe(async {
        proxy
            .execute_message(ProxyMessage::DeregisterMiner { owner: other_owner })
            .await;
    })
    .catch_unwind()
    .await;

    assert!(result.is_err());
    assert_eq!(
        state
            .borrow()
            .miners
            .contains_key(&registered)
            .blocking_wait()
            .unwrap(),
        true
    );
}

#[tokio::test(flavor = "multi_thread")]
async fn msg_propose_add_operator_records_first_vote_but_not_final_approval() {
    let operator_1 = test_account(
        "aee928d4bf3880353b4a3cd9b6f88e6cc6e5ed050860abae439e7782e9b2dfe8",
        "0x02e900512d2fca22897f80a2f6932ff454f2752ef7afad18729dd25e5b5b6e00",
    );
    let operator_2 = test_account(
        "aee928d4bf3880353b4a3cd9b6f88e6cc6e5ed050860abae439e7782e9b2dfe8",
        "0x02e900512d2fca22897f80a2f6932ff454f2752ef7afad18729dd25e5b5b6e01",
    );
    let operator_3 = test_account(
        "aee928d4bf3880353b4a3cd9b6f88e6cc6e5ed050860abae439e7782e9b2dfe8",
        "0x02e900512d2fca22897f80a2f6932ff454f2752ef7afad18729dd25e5b5b6e02",
    );
    let candidate = test_account(
        "aee928d4bf3880353b4a3cd9b6f88e6cc6e5ed050860abae439e7782e9b2dfe8",
        "0x02e900512d2fca22897f80a2f6932ff454f2752ef7afad18729dd25e5b5b6e03",
    );
    let (mut proxy, state) =
        create_and_instantiate_proxy_with_operators(vec![operator_1, operator_2, operator_3]);

    proxy
        .execute_message(ProxyMessage::ProposeAddOperator {
            operator: operator_1,
            owner: candidate,
        })
        .await;

    let approval = state
        .borrow()
        .operators
        .get(&candidate)
        .blocking_wait()
        .unwrap()
        .unwrap();
    assert_eq!(approval.voted(operator_1), true);
    assert_eq!(approval.approved(), false);
}

#[tokio::test(flavor = "multi_thread")]
async fn msg_approve_add_operator_second_vote_completes_approval() {
    let operator_1 = test_account(
        "aee928d4bf3880353b4a3cd9b6f88e6cc6e5ed050860abae439e7782e9b2dfe8",
        "0x02e900512d2fca22897f80a2f6932ff454f2752ef7afad18729dd25e5b5b6e00",
    );
    let operator_2 = test_account(
        "aee928d4bf3880353b4a3cd9b6f88e6cc6e5ed050860abae439e7782e9b2dfe8",
        "0x02e900512d2fca22897f80a2f6932ff454f2752ef7afad18729dd25e5b5b6e01",
    );
    let operator_3 = test_account(
        "aee928d4bf3880353b4a3cd9b6f88e6cc6e5ed050860abae439e7782e9b2dfe8",
        "0x02e900512d2fca22897f80a2f6932ff454f2752ef7afad18729dd25e5b5b6e02",
    );
    let candidate = test_account(
        "aee928d4bf3880353b4a3cd9b6f88e6cc6e5ed050860abae439e7782e9b2dfe8",
        "0x02e900512d2fca22897f80a2f6932ff454f2752ef7afad18729dd25e5b5b6e03",
    );
    let (mut proxy, state) =
        create_and_instantiate_proxy_with_operators(vec![operator_1, operator_2, operator_3]);

    proxy
        .execute_message(ProxyMessage::ProposeAddOperator {
            operator: operator_1,
            owner: candidate,
        })
        .await;
    proxy
        .execute_message(ProxyMessage::ApproveAddOperator {
            operator: operator_2,
            owner: candidate,
        })
        .await;

    let approval = state
        .borrow()
        .operators
        .get(&candidate)
        .blocking_wait()
        .unwrap()
        .unwrap();
    assert_eq!(approval.voted(operator_1), true);
    assert_eq!(approval.voted(operator_2), true);
    assert_eq!(approval.approved(), true);
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic(expected = "Invalid operator")]
async fn msg_approve_add_operator_rejects_non_operator_voter() {
    let operator_1 = test_account(
        "aee928d4bf3880353b4a3cd9b6f88e6cc6e5ed050860abae439e7782e9b2dfe8",
        "0x02e900512d2fca22897f80a2f6932ff454f2752ef7afad18729dd25e5b5b6e00",
    );
    let operator_2 = test_account(
        "aee928d4bf3880353b4a3cd9b6f88e6cc6e5ed050860abae439e7782e9b2dfe8",
        "0x02e900512d2fca22897f80a2f6932ff454f2752ef7afad18729dd25e5b5b6e01",
    );
    let operator_3 = test_account(
        "aee928d4bf3880353b4a3cd9b6f88e6cc6e5ed050860abae439e7782e9b2dfe8",
        "0x02e900512d2fca22897f80a2f6932ff454f2752ef7afad18729dd25e5b5b6e02",
    );
    let outsider = test_account(
        "aee928d4bf3880353b4a3cd9b6f88e6cc6e5ed050860abae439e7782e9b2dfe8",
        "0x02e900512d2fca22897f80a2f6932ff454f2752ef7afad18729dd25e5b5b6e09",
    );
    let candidate = test_account(
        "aee928d4bf3880353b4a3cd9b6f88e6cc6e5ed050860abae439e7782e9b2dfe8",
        "0x02e900512d2fca22897f80a2f6932ff454f2752ef7afad18729dd25e5b5b6e03",
    );
    let (mut proxy, _state) =
        create_and_instantiate_proxy_with_operators(vec![operator_1, operator_2, operator_3]);

    proxy
        .execute_message(ProxyMessage::ProposeAddOperator {
            operator: operator_1,
            owner: candidate,
        })
        .await;
    proxy
        .execute_message(ProxyMessage::ApproveAddOperator {
            operator: outsider,
            owner: candidate,
        })
        .await;
}

#[tokio::test(flavor = "multi_thread")]
async fn msg_propose_ban_operator_records_first_vote_but_keeps_target_active() {
    let operator_1 = test_account(
        "aee928d4bf3880353b4a3cd9b6f88e6cc6e5ed050860abae439e7782e9b2dfe8",
        "0x02e900512d2fca22897f80a2f6932ff454f2752ef7afad18729dd25e5b5b6e00",
    );
    let operator_2 = test_account(
        "aee928d4bf3880353b4a3cd9b6f88e6cc6e5ed050860abae439e7782e9b2dfe8",
        "0x02e900512d2fca22897f80a2f6932ff454f2752ef7afad18729dd25e5b5b6e01",
    );
    let operator_3 = test_account(
        "aee928d4bf3880353b4a3cd9b6f88e6cc6e5ed050860abae439e7782e9b2dfe8",
        "0x02e900512d2fca22897f80a2f6932ff454f2752ef7afad18729dd25e5b5b6e02",
    );
    let (mut proxy, state) =
        create_and_instantiate_proxy_with_operators(vec![operator_1, operator_2, operator_3]);

    proxy
        .execute_message(ProxyMessage::ProposeBanOperator {
            operator: operator_1,
            owner: operator_2,
        })
        .await;

    let approval = state
        .borrow()
        .banning_operators
        .get(&operator_2)
        .blocking_wait()
        .unwrap()
        .unwrap();
    assert_eq!(approval.voted(operator_1), true);
    assert_eq!(approval.approved(), false);
    assert_eq!(
        state
            .borrow()
            .operators
            .contains_key(&operator_2)
            .blocking_wait()
            .unwrap(),
        true
    );
}

#[tokio::test(flavor = "multi_thread")]
async fn msg_approve_ban_operator_second_vote_removes_operator() {
    let operator_1 = test_account(
        "aee928d4bf3880353b4a3cd9b6f88e6cc6e5ed050860abae439e7782e9b2dfe8",
        "0x02e900512d2fca22897f80a2f6932ff454f2752ef7afad18729dd25e5b5b6e00",
    );
    let operator_2 = test_account(
        "aee928d4bf3880353b4a3cd9b6f88e6cc6e5ed050860abae439e7782e9b2dfe8",
        "0x02e900512d2fca22897f80a2f6932ff454f2752ef7afad18729dd25e5b5b6e01",
    );
    let operator_3 = test_account(
        "aee928d4bf3880353b4a3cd9b6f88e6cc6e5ed050860abae439e7782e9b2dfe8",
        "0x02e900512d2fca22897f80a2f6932ff454f2752ef7afad18729dd25e5b5b6e02",
    );
    let (mut proxy, state) =
        create_and_instantiate_proxy_with_operators(vec![operator_1, operator_2, operator_3]);

    proxy
        .execute_message(ProxyMessage::ProposeBanOperator {
            operator: operator_1,
            owner: operator_2,
        })
        .await;
    proxy
        .execute_message(ProxyMessage::ApproveBanOperator {
            operator: operator_3,
            owner: operator_2,
        })
        .await;

    assert_eq!(
        state
            .borrow()
            .operators
            .contains_key(&operator_2)
            .blocking_wait()
            .unwrap(),
        false
    );
    assert_eq!(
        state
            .borrow()
            .banning_operators
            .contains_key(&operator_2)
            .blocking_wait()
            .unwrap(),
        false
    );
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic(expected = "Failed: construct message handler: NotAllowed")]
async fn msg_create_meme_ext_rejects_creator_chain_execution() {
    let (mut proxy, state) = create_and_instantiate_proxy();
    let bytecode_id = state.borrow().meme_bytecode_id();
    let state_bytecode_ids = state
        .borrow()
        .meme_state_bytecode_ids()
        .blocking_wait()
        .unwrap();

    proxy
        .execute_message(ProxyMessage::CreateMemeExt {
            bytecode_id,
            state_bytecode_ids,
            instantiation_argument: test_meme_instantiation_argument(),
            parameters: test_meme_parameters(),
        })
        .await;
}

#[tokio::test(flavor = "multi_thread")]
async fn op_register_miner_on_user_chain_emits_creator_chain_message() {
    let (mut proxy, _state) = create_and_instantiate_proxy();
    let creator_chain_id = proxy.runtime.borrow_mut().application_creator_chain_id();
    let user_chain_id =
        ChainId::from_str("abdb7c1079f36eaa03f629540283a881eb4256d1ece83a84415022d4d2a9ac65")
            .unwrap();
    proxy.runtime.borrow_mut().set_chain_id(user_chain_id);

    let response = proxy
        .execute_operation(ProxyOperation::RegisterMiner)
        .now_or_never()
        .expect("Execution of proxy operation should not await anything");

    assert!(matches!(response, ProxyResponse::Ok));
    let runtime = proxy.runtime.borrow();
    let requests = runtime.created_send_message_requests();
    let request = requests.last().unwrap();
    assert_eq!(request.destination, creator_chain_id);
    assert!(request.authenticated);
    assert!(!request.is_tracked);
    assert!(matches!(
        request.message,
        ProxyMessage::RegisterMiner { .. }
    ));
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic(expected = "Failed: construct message handler: NotAllowed")]
async fn msg_meme_created_rejects_user_chain_execution() {
    let (mut proxy, _state) = create_and_instantiate_proxy();
    let user_chain_id =
        ChainId::from_str("abdb7c1079f36eaa03f629540283a881eb4256d1ece83a84415022d4d2a9ac65")
            .unwrap();
    let token =
        ApplicationId::from_str("b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bae")
            .unwrap();
    proxy.runtime.borrow_mut().set_chain_id(user_chain_id);

    proxy
        .execute_message(ProxyMessage::MemeCreated {
            chain_id: user_chain_id,
            token,
        })
        .await;
}

#[tokio::test(flavor = "multi_thread")]
async fn msg_meme_created_sets_chain_token_for_existing_chain() {
    let (mut proxy, state) = create_and_instantiate_proxy();
    let chain_id =
        ChainId::from_str("abdb7c1079f36eaa03f629540283a881eb4256d1ece83a84415022d4d2a9ac65")
            .unwrap();
    let token =
        ApplicationId::from_str("b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bae")
            .unwrap();

    state
        .borrow_mut()
        .create_chain(chain_id, Timestamp::from(0))
        .unwrap();

    proxy
        .execute_message(ProxyMessage::MemeCreated { chain_id, token })
        .await;

    assert_eq!(
        state
            .borrow()
            .chains
            .get(&chain_id)
            .blocking_wait()
            .unwrap()
            .unwrap()
            .token,
        Some(token)
    );
}

#[tokio::test(flavor = "multi_thread")]
async fn msg_meme_created_ignores_unknown_chain_receipt() {
    let (mut proxy, state) = create_and_instantiate_proxy();
    let chain_id =
        ChainId::from_str("abdb7c1079f36eaa03f629540283a881eb4256d1ece83a84415022d4d2a9ac65")
            .unwrap();
    let token =
        ApplicationId::from_str("b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bae")
            .unwrap();

    proxy
        .execute_message(ProxyMessage::MemeCreated { chain_id, token })
        .await;

    assert_eq!(
        state
            .borrow()
            .chains
            .contains_key(&chain_id)
            .blocking_wait()
            .unwrap(),
        false
    );
}

#[tokio::test(flavor = "multi_thread")]
async fn msg_meme_created_is_idempotent_for_same_receipt() {
    let (mut proxy, state) = create_and_instantiate_proxy();
    let chain_id =
        ChainId::from_str("abdb7c1079f36eaa03f629540283a881eb4256d1ece83a84415022d4d2a9ac65")
            .unwrap();
    let token =
        ApplicationId::from_str("b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bae")
            .unwrap();

    state
        .borrow_mut()
        .create_chain(chain_id, Timestamp::from(0))
        .unwrap();

    proxy
        .execute_message(ProxyMessage::MemeCreated { chain_id, token })
        .await;
    proxy
        .execute_message(ProxyMessage::MemeCreated { chain_id, token })
        .await;

    assert_eq!(
        state
            .borrow()
            .chains
            .get(&chain_id)
            .blocking_wait()
            .unwrap()
            .unwrap()
            .token,
        Some(token)
    );
}

#[tokio::test(flavor = "multi_thread")]
async fn op_set_meme_bytecode_ids_updates_business_and_state_bytecodes() {
    let (mut proxy, state) = create_and_instantiate_proxy();

    let new_business_bytecode_id = ModuleId::from_str(
        "c94e486abcfc016e937dad4297523060095f405530c95d498d981a94141589f167693295a14c3b48460ad6f75d67d2414428227550eb8cee8ecaa37e8646518300",
    )
    .unwrap();
    let new_state_bytecode_id = ModuleId::from_str(
        "d94e486abcfc016e937dad4297523060095f405530c95d498d981a94141589f167693295a14c3b48460ad6f75d67d2414428227550eb8cee8ecaa37e8646518300",
    )
    .unwrap();

    proxy
        .execute_operation(ProxyOperation::SetMemeBytecodeIds {
            business_bytecode_id: new_business_bytecode_id,
            state_bytecode_id: new_state_bytecode_id,
        })
        .await;

    assert_eq!(
        state.borrow().meme_bytecode_id.get().unwrap(),
        new_business_bytecode_id
    );
    assert_eq!(
        state
            .borrow()
            .meme_state_bytecode_ids
            .get(&2)
            .blocking_wait()
            .unwrap()
            .unwrap(),
        new_state_bytecode_id
    );
}

#[tokio::test(flavor = "multi_thread")]
async fn msg_create_meme_ext_creates_apps_appends_states_and_initializes() {
    let (mut proxy, state) = create_and_instantiate_proxy();
    let (proxy_application_id, creator_chain_id) = {
        let mut runtime = proxy.runtime.borrow_mut();
        (
            runtime.application_id().forget_abi(),
            runtime.application_creator_chain_id(),
        )
    };
    let meme_chain_id =
        ChainId::from_str("abdb7c1079f36eaa03f629540283a881eb4256d1ece83a84415022d4d2a9ac65")
            .unwrap();

    proxy.runtime.borrow_mut().set_chain_id(meme_chain_id);
    proxy
        .runtime
        .borrow_mut()
        .set_authenticated_caller_id(Some(proxy_application_id));

    let business_application_id =
        ApplicationId::from_str("c10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bad")
            .unwrap();
    let meme_state_application_id =
        ApplicationId::from_str("c20ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bae")
            .unwrap();

    let bytecode_id = state.borrow().meme_bytecode_id();
    let state_bytecode_id = state
        .borrow()
        .meme_state_bytecode_ids()
        .blocking_wait()
        .unwrap()
        .into_iter()
        .next()
        .map(|(_, bytecode_id)| bytecode_id)
        .expect("Missing meme state bytecode id");

    let mut instantiation_argument = test_meme_instantiation_argument();
    instantiation_argument.proxy_application_id = Some(proxy_application_id);

    let mut parameters = test_meme_parameters();
    parameters.creator = test_account(
        "abdb7c1079f36eaa03f629540283a881eb4256d1ece83a84415022d4d2a9ac65",
        "0x02e900512d2fca22897f80a2f6932ff454f2752ef7afad18729dd25e5b5b6e88",
    );

    let state_instantiation_argument = MemeStateInstantiationArgument {
        business_application_id,
        operator: Some(parameters.creator),
        proxy_application_id: Some(proxy_application_id),
    };

    proxy
        .runtime
        .borrow_mut()
        .add_expected_create_application_call(
            bytecode_id,
            &parameters,
            &instantiation_argument,
            vec![],
            business_application_id,
        );
    proxy
        .runtime
        .borrow_mut()
        .add_expected_create_application_call(
            state_bytecode_id,
            &(),
            &state_instantiation_argument,
            vec![],
            meme_state_application_id,
        );

    let state_for_handler = state.clone();
    proxy.runtime.borrow_mut().set_call_application_handler(
        move |_authenticated, application_id, call| {
            if application_id == state_application_id() {
                return dispatch_state_operation(&mut state_for_handler.borrow_mut(), &call);
            }
            assert_eq!(application_id, business_application_id);
            let operation: MemeOperation =
                bcs::from_bytes(&call).expect("Failed to decode meme operation");
            match operation {
                MemeOperation::AppendStates {
                    state_application_ids,
                } => {
                    assert_eq!(state_application_ids, vec![meme_state_application_id]);
                }
                MemeOperation::Initialize { argument } => {
                    assert_eq!(
                        argument.blob_gateway_application_id,
                        instantiation_argument.blob_gateway_application_id
                    );
                    assert_eq!(
                        argument.ams_application_id,
                        instantiation_argument.ams_application_id
                    );
                    assert_eq!(
                        argument.swap_application_id,
                        instantiation_argument.swap_application_id
                    );
                    assert_eq!(argument.enable_mining, parameters.enable_mining);
                    assert_eq!(argument.mining_supply, parameters.mining_supply);
                }
                _ => panic!("Unexpected meme operation: {:?}", operation),
            }
            bcs::to_bytes(&MemeResponse::Ok).expect("Failed to encode meme response")
        },
    );

    proxy
        .runtime
        .borrow_mut()
        .set_application_permissions(ApplicationPermissions::default());
    proxy
        .runtime
        .borrow_mut()
        .set_can_change_application_permissions(true);

    proxy
        .execute_message(ProxyMessage::CreateMemeExt {
            bytecode_id,
            state_bytecode_ids: vec![(1, state_bytecode_id)],
            instantiation_argument,
            parameters,
        })
        .await;

    let runtime = proxy.runtime.borrow();
    let requests = runtime.created_send_message_requests();
    let request = requests.last().expect("Missing MemeCreated message");
    assert_eq!(request.destination, creator_chain_id);
    assert!(matches!(
        request.message,
        ProxyMessage::MemeCreated {
            chain_id,
            token,
        } if chain_id == meme_chain_id && token == business_application_id
    ));
}

#[test]
fn cross_application_call() {}

#[tokio::test(flavor = "multi_thread")]
async fn op_handoff_updates_state_business_application_id() {
    let (mut proxy, state) = create_and_instantiate_proxy();
    let new_business_app_id = ApplicationId::from_str(
        "c10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bad",
    )
    .unwrap();

    proxy
        .execute_operation(ProxyOperation::Handoff {
            new_business_application_id: new_business_app_id,
        })
        .await;

    assert_eq!(
        state.borrow().business_application_id.get().unwrap(),
        new_business_app_id
    );
}

fn state_application_id() -> ApplicationId {
    ApplicationId::from_str("b20ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bad")
        .unwrap()
}

fn dispatch_state_operation(state: &mut StateAppState, operation: &[u8]) -> Vec<u8> {
    let operation = bcs::from_bytes::<ProxyStateV1Operation>(operation)
        .expect("Failed to deserialize proxy state v1 operation");
    let response: Result<ProxyStateV1Response, proxy_state::state::errors::StateError> = match operation {
        ProxyStateV1Operation::SetMemeBytecodeIds {
            business_bytecode_id,
            state_bytecode_id,
        } => state
            .set_meme_bytecode_ids(business_bytecode_id, state_bytecode_id)
            .blocking_wait()
            .map(|_| ProxyStateV1Response::Ok),
        ProxyStateV1Operation::Initialize { argument } => state
            .initialize(argument)
            .blocking_wait()
            .map(|_| ProxyStateV1Response::Ok),
        ProxyStateV1Operation::AddOperator { owner } => state
            .add_operator(owner)
            .blocking_wait()
            .map(|_| ProxyStateV1Response::Ok),
        ProxyStateV1Operation::ApproveAddOperator { owner, operator } => state
            .approve_add_operator(owner, operator)
            .blocking_wait()
            .map(|_| ProxyStateV1Response::Ok),
        ProxyStateV1Operation::BanOperator { owner } => state
            .ban_operator(owner)
            .blocking_wait()
            .map(|_| ProxyStateV1Response::Ok),
        ProxyStateV1Operation::ApproveBanOperator { owner, operator } => state
            .approve_ban_operator(owner, operator)
            .blocking_wait()
            .map(|_| ProxyStateV1Response::Ok),
        ProxyStateV1Operation::AddGenesisMiner { owner } => state
            .add_genesis_miner(owner)
            .blocking_wait()
            .map(|_| ProxyStateV1Response::Ok),
        ProxyStateV1Operation::ApproveAddGenesisMiner { owner, operator } => state
            .approve_add_genesis_miner(owner, operator)
            .blocking_wait()
            .map(|_| ProxyStateV1Response::Ok),
        ProxyStateV1Operation::RemoveGenesisMiner { owner } => state
            .remove_genesis_miner(owner)
            .blocking_wait()
            .map(|_| ProxyStateV1Response::Ok),
        ProxyStateV1Operation::ApproveRemoveGenesisMiner { owner, operator } => state
            .approve_remove_genesis_miner(owner, operator)
            .blocking_wait()
            .map(|_| ProxyStateV1Response::Ok),
        ProxyStateV1Operation::RegisterMiner { owner, now } => state
            .register_miner(owner, now)
            .blocking_wait()
            .map(|_| ProxyStateV1Response::Ok),
        ProxyStateV1Operation::DeregisterMiner { owner } => state
            .deregister_miner(owner)
            .blocking_wait()
            .map(|_| ProxyStateV1Response::Ok),
        ProxyStateV1Operation::CreateChain { chain_id, created_at } => state
            .create_chain(chain_id, created_at)
            .map(|_| ProxyStateV1Response::Ok),
        ProxyStateV1Operation::CreateChainToken { chain_id, token } => state
            .create_chain_token(chain_id, token)
            .blocking_wait()
            .map(|_| ProxyStateV1Response::Ok),
        ProxyStateV1Operation::MemeBytecodeId => Ok(ProxyStateV1Response::ModuleId(state.meme_bytecode_id())),
        ProxyStateV1Operation::MemeStateBytecodeIds => state
            .meme_state_bytecode_ids()
            .blocking_wait()
            .map(ProxyStateV1Response::ModuleIds),
        ProxyStateV1Operation::SwapApplicationId => Ok(ProxyStateV1Response::ApplicationId(state.swap_application_id())),
        ProxyStateV1Operation::IsGenesisMiner { owner } => state
            .is_genesis_miner(owner)
            .blocking_wait()
            .map(ProxyStateV1Response::Bool),
        ProxyStateV1Operation::Miners => state
            .miners()
            .blocking_wait()
            .map(ProxyStateV1Response::Miners),
        ProxyStateV1Operation::MinerOwners => state
            .miner_owners()
            .blocking_wait()
            .map(ProxyStateV1Response::AccountOwners),
        ProxyStateV1Operation::GenesisMiners => state
            .genesis_miners()
            .blocking_wait()
            .map(ProxyStateV1Response::Miners),
        ProxyStateV1Operation::Chain { chain_id } => state
            .chain(chain_id)
            .blocking_wait()
            .map(ProxyStateV1Response::Chain),
        ProxyStateV1Operation::Chains { created_after } => state
            .chains(created_after)
            .blocking_wait()
            .map(ProxyStateV1Response::Chains),
        ProxyStateV1Operation::ChainByToken { token } => state
            .chain_by_token(token)
            .blocking_wait()
            .map(ProxyStateV1Response::Chain),
        ProxyStateV1Operation::ValidateOperator { owner } => state
            .validate_operator(owner)
            .blocking_wait()
            .map(|_| ProxyStateV1Response::Ok),
        ProxyStateV1Operation::SetOperator { new_operator } => state
            .set_operator(new_operator)
            .blocking_wait()
            .map(|_| ProxyStateV1Response::Ok),
        ProxyStateV1Operation::Handoff {
            new_business_application_id,
        } => state
            .handoff(new_business_application_id)
            .blocking_wait()
            .map(|_| ProxyStateV1Response::Ok),
    };
    match response {
        Ok(response) => bcs::to_bytes(&response).expect("Failed to serialize state response"),
        Err(error) => bcs::to_bytes(&ProxyStateV1Response::Fail(format!("{}", error)))
            .expect("Failed to serialize state response"),
    }
}

fn create_and_instantiate_proxy() -> (ProxyContract, Rc<RefCell<StateAppState>>) {
    create_and_instantiate_proxy_with_operators(vec![test_account(
        "aee928d4bf3880353b4a3cd9b6f88e6cc6e5ed050860abae439e7782e9b2dfe8",
        "0x02e900512d2fca22897f80a2f6932ff454f2752ef7afad18729dd25e5b5b6e00",
    )])
}

fn create_and_instantiate_proxy_with_operators(
    operators: Vec<Account>,
) -> (ProxyContract, Rc<RefCell<StateAppState>>) {
    let chain_id =
        ChainId::from_str("aee928d4bf3880353b4a3cd9b6f88e6cc6e5ed050860abae439e7782e9b2dfe8")
            .unwrap();
    let owner = operators[0].owner;
    let application_id =
        ApplicationId::from_str("b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bad")
            .unwrap()
            .with_abi::<ProxyAbi>();
    let runtime = ContractRuntime::new()
        .with_application_parameters(())
        .with_authenticated_signer(owner)
        .with_chain_id(chain_id)
        .with_application_creator_chain_id(chain_id)
        .with_chain_ownership(ChainOwnership::single(owner))
        .with_system_time(Timestamp::from(0))
        .with_application_id(application_id);
    let mut contract = ProxyContract {
        state: Rc::new(RefCell::new(
            BusinessState::load(runtime.root_view_storage_context())
                .blocking_wait()
                .expect("Failed to read from mock key value store"),
        )),
        runtime: Rc::new(RefCell::new(runtime)),
    };

    let meme_bytecode_id = ModuleId::from_str("b94e486abcfc016e937dad4297523060095f405530c95d498d981a94141589f167693295a14c3b48460ad6f75d67d2414428227550eb8cee8ecaa37e8646518300").unwrap();
    let meme_state_bytecode_id = ModuleId::from_str("a94e486abcfc016e937dad4297523060095f405530c95d498d981a94141589f167693295a14c3b48460ad6f75d67d2414428227550eb8cee8ecaa37e8646518300").unwrap();

    let owners = vec![operators[0]];
    let state_instantiation_argument = StateInstantiationArgument {
        business_application_id: application_id.forget_abi(),
        operator: owners.first().copied(),
    };

    contract
        .instantiate(InstantiationArgument {})
        .blocking_wait();

    let mut state_app_state = StateAppState::load(contract.runtime.borrow_mut().root_view_storage_context())
        .blocking_wait()
        .expect("Failed to load proxy state v1");
    state_app_state
        .instantiate(state_instantiation_argument)
        .expect("Failed to instantiate proxy state v1");
    let state_app_state = Rc::new(RefCell::new(state_app_state));

    contract.state
        .borrow_mut()
        .state_applications
        .insert(&1, state_application_id())
        .expect("Failed to append proxy state v1");
    contract.state.borrow_mut().latest_state_version.set(1);

    let state_app_state_for_handler = state_app_state.clone();
    contract.runtime.borrow_mut().set_call_application_handler(
        move |_authenticated, app_id, operation| {
            if app_id != state_application_id() {
                panic!("Unexpected call_application to {}", app_id);
            }
            dispatch_state_operation(&mut state_app_state_for_handler.borrow_mut(), &operation)
        },
    );

    contract
        .execute_operation(ProxyOperation::Initialize {
            argument: InitializeArgument {
                initial_operators: operators.clone(),
                genesis_miner_owners: owners.clone(),
                swap_application_id: application_id.forget_abi(),
                meme_bytecode_id,
                meme_state_bytecode_ids: vec![StateBytecodeId {
                    version: 1,
                    module_id: meme_state_bytecode_id,
                }],
            },
        })
        .blocking_wait();

    assert_eq!(
        contract
            .state
            .borrow()
            .latest_state_version
            .get()
            .clone(),
        1u16
    );
    assert_eq!(
        contract
            .state
            .borrow()
            .state_applications
            .get(&1)
            .blocking_wait()
            .unwrap()
            .unwrap(),
        state_application_id()
    );

    (contract, state_app_state)
}

fn test_account(chain_id: &str, owner: &str) -> Account {
    Account {
        chain_id: ChainId::from_str(chain_id).unwrap(),
        owner: AccountOwner::from_str(owner).unwrap(),
    }
}

fn test_meme_instantiation_argument() -> MemeInstantiationArgument {
    MemeInstantiationArgument {
        meme: Meme {
            name: "Test Token".to_string(),
            ticker: "LTT".to_string(),
            decimals: 6,
            initial_supply: linera_sdk::linera_base_types::Amount::from_tokens(1000),
            total_supply: linera_sdk::linera_base_types::Amount::from_tokens(1000),
            metadata: Metadata {
                logo_store_type: StoreType::S3,
                logo: None,
                description: "Test".to_string(),
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
        swap_application_id: None,
    }
}

fn test_meme_parameters() -> MemeParameters {
    MemeParameters {
        creator: test_account(
            "abdb7c1079f36eaa03f629540283a881eb4256d1ece83a84415022d4d2a9ac65",
            "0x02e900512d2fca22897f80a2f6932ff454f2752ef7afad18729dd25e5b5b6e88",
        ),
        initial_liquidity: None,
        virtual_initial_liquidity: true,
        swap_creator_chain_id: ChainId::from_str(
            "abdb7c1079f36eaa03f629540283a881eb4256d1ece83a84415022d4d2a9ac65",
        )
        .unwrap(),
        enable_mining: false,
        mining_supply: None,
    }
}
