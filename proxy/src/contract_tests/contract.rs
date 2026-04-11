use super::super::{ProxyContract, ProxyState};

use abi::approval::Approval;
use abi::meme::{
    InstantiationArgument as MemeInstantiationArgument, Meme, MemeParameters, Metadata,
};
use abi::proxy::{InstantiationArgument, ProxyAbi, ProxyMessage, ProxyOperation, ProxyResponse};
use abi::store_type::StoreType;
use futures::FutureExt as _;
use linera_sdk::{
    linera_base_types::{
        Account, AccountOwner, ApplicationId, ChainId, ChainOwnership, ModuleId, Timestamp,
    },
    util::BlockingWait,
    views::View,
    Contract, ContractRuntime,
};
use proxy::interfaces::state::StateInterface;
use std::str::FromStr;
use std::{cell::RefCell, rc::Rc};

#[test]
#[should_panic(expected = "Failed: construct operation handler: NotAllowed")]
fn op_propose_add_genesis_miner() {
    let _ = env_logger::builder().is_test(true).try_init();
    let mut proxy = create_and_instantiate_proxy();

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
    let mut proxy = create_and_instantiate_proxy();

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
        proxy.state.borrow().is_genesis_miner(owner).await.unwrap(),
        true
    );
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic(expected = "Already registered")]
async fn msg_register_miner_rejects_duplicate_owner_on_different_chain() {
    let mut proxy = create_and_instantiate_proxy();
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
#[should_panic(expected = "Not exists")]
async fn msg_deregister_miner_rejects_unregistered_owner() {
    let mut proxy = create_and_instantiate_proxy();
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
    let mut proxy = create_and_instantiate_proxy();
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
        proxy
            .state
            .borrow()
            .miners
            .contains_key(&registered)
            .await
            .unwrap(),
        true
    );
}

#[tokio::test(flavor = "multi_thread")]
async fn msg_deregister_miner_rejects_other_owner_without_touching_registered_miner() {
    let mut proxy = create_and_instantiate_proxy();
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
        proxy
            .state
            .borrow()
            .miners
            .contains_key(&registered)
            .await
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
    let mut proxy =
        create_and_instantiate_proxy_with_operators(vec![operator_1, operator_2, operator_3]);

    proxy
        .execute_message(ProxyMessage::ProposeAddOperator {
            operator: operator_1,
            owner: candidate,
        })
        .await;

    let approval: Approval = proxy
        .state
        .borrow()
        .operators
        .get(&candidate)
        .await
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
    let mut proxy =
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

    let approval: Approval = proxy
        .state
        .borrow()
        .operators
        .get(&candidate)
        .await
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
    let mut proxy =
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
    let mut proxy =
        create_and_instantiate_proxy_with_operators(vec![operator_1, operator_2, operator_3]);

    proxy
        .execute_message(ProxyMessage::ProposeBanOperator {
            operator: operator_1,
            owner: operator_2,
        })
        .await;

    let approval: Approval = proxy
        .state
        .borrow()
        .banning_operators
        .get(&operator_2)
        .await
        .unwrap()
        .unwrap();
    assert_eq!(approval.voted(operator_1), true);
    assert_eq!(approval.approved(), false);
    assert_eq!(
        proxy
            .state
            .borrow()
            .operators
            .contains_key(&operator_2)
            .await
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
    let mut proxy =
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
        proxy
            .state
            .borrow()
            .operators
            .contains_key(&operator_2)
            .await
            .unwrap(),
        false
    );
    assert_eq!(
        proxy
            .state
            .borrow()
            .banning_operators
            .contains_key(&operator_2)
            .await
            .unwrap(),
        false
    );
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic(expected = "Failed: construct message handler: NotAllowed")]
async fn msg_create_meme_ext_rejects_creator_chain_execution() {
    let mut proxy = create_and_instantiate_proxy();
    let bytecode_id = proxy.state.borrow().meme_bytecode_id();

    proxy
        .execute_message(ProxyMessage::CreateMemeExt {
            bytecode_id,
            instantiation_argument: test_meme_instantiation_argument(),
            parameters: test_meme_parameters(),
        })
        .await;
}

#[tokio::test(flavor = "multi_thread")]
async fn msg_meme_created_sets_chain_token_for_existing_chain() {
    let mut proxy = create_and_instantiate_proxy();
    let chain_id =
        ChainId::from_str("abdb7c1079f36eaa03f629540283a881eb4256d1ece83a84415022d4d2a9ac65")
            .unwrap();
    let token =
        ApplicationId::from_str("b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bae")
            .unwrap();

    proxy
        .state
        .borrow_mut()
        .create_chain(chain_id, Timestamp::from(0))
        .unwrap();

    proxy
        .execute_message(ProxyMessage::MemeCreated { chain_id, token })
        .await;

    assert_eq!(
        proxy
            .state
            .borrow()
            .chains
            .get(&chain_id)
            .await
            .unwrap()
            .unwrap()
            .token,
        Some(token)
    );
}

#[tokio::test(flavor = "multi_thread")]
async fn msg_meme_created_ignores_unknown_chain_receipt() {
    let mut proxy = create_and_instantiate_proxy();
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
        proxy
            .state
            .borrow()
            .chains
            .contains_key(&chain_id)
            .await
            .unwrap(),
        false
    );
}

#[tokio::test(flavor = "multi_thread")]
async fn msg_meme_created_is_idempotent_for_same_receipt() {
    let mut proxy = create_and_instantiate_proxy();
    let chain_id =
        ChainId::from_str("abdb7c1079f36eaa03f629540283a881eb4256d1ece83a84415022d4d2a9ac65")
            .unwrap();
    let token =
        ApplicationId::from_str("b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bae")
            .unwrap();

    proxy
        .state
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
        proxy
            .state
            .borrow()
            .chains
            .get(&chain_id)
            .await
            .unwrap()
            .unwrap()
            .token,
        Some(token)
    );
}

#[test]
fn cross_application_call() {}

fn create_and_instantiate_proxy() -> ProxyContract {
    create_and_instantiate_proxy_with_operators(vec![test_account(
        "aee928d4bf3880353b4a3cd9b6f88e6cc6e5ed050860abae439e7782e9b2dfe8",
        "0x02e900512d2fca22897f80a2f6932ff454f2752ef7afad18729dd25e5b5b6e00",
    )])
}

fn create_and_instantiate_proxy_with_operators(operators: Vec<Account>) -> ProxyContract {
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
            ProxyState::load(runtime.root_view_storage_context())
                .blocking_wait()
                .expect("Failed to read from mock key value store"),
        )),
        runtime: Rc::new(RefCell::new(runtime)),
    };

    let meme_bytecode_id = ModuleId::from_str("b94e486abcfc016e937dad4297523060095f405530c95d498d981a94141589f167693295a14c3b48460ad6f75d67d2414428227550eb8cee8ecaa37e8646518300").unwrap();

    contract
        .instantiate(InstantiationArgument {
            meme_bytecode_id,
            operators,
            swap_application_id: application_id.forget_abi(),
        })
        .now_or_never()
        .expect("Initialization of proxy state should not await anything");

    assert_eq!(
        contract.state.borrow().meme_bytecode_id.get().unwrap(),
        meme_bytecode_id
    );

    contract
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
