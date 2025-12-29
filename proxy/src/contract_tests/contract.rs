use super::super::{ProxyContract, ProxyState};

use abi::proxy::{InstantiationArgument, ProxyAbi, ProxyMessage, ProxyOperation, ProxyResponse};
use futures::FutureExt as _;
use linera_sdk::{
    linera_base_types::{Account, AccountOwner, ApplicationId, ChainId, ChainOwnership, ModuleId},
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

#[test]
fn cross_application_call() {}

fn create_and_instantiate_proxy() -> ProxyContract {
    let chain_id =
        ChainId::from_str("aee928d4bf3880353b4a3cd9b6f88e6cc6e5ed050860abae439e7782e9b2dfe8")
            .unwrap();
    let owner = AccountOwner::from_str(
        "0x02e900512d2fca22897f80a2f6932ff454f2752ef7afad18729dd25e5b5b6e00",
    )
    .unwrap();
    let operator = Account { chain_id, owner };
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
            operators: vec![operator],
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
