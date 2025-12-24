use super::super::{SwapContract, SwapState};

use abi::{
    meme::MemeResponse,
    swap::router::{InstantiationArgument, SwapAbi, SwapOperation, SwapParameters, SwapResponse},
};
use futures::FutureExt as _;
use linera_sdk::{
    bcs,
    linera_base_types::{
        Account, AccountOwner, Amount, ApplicationId, ApplicationPermissions, ChainId,
        ChainOwnership, ModuleId,
    },
    util::BlockingWait,
    views::View,
    Contract, ContractRuntime,
};
use std::str::FromStr;
use std::{cell::RefCell, rc::Rc};

#[tokio::test(flavor = "multi_thread")]
async fn operation_initialize_liquidity() {
    let mut swap = create_and_instantiate_swap();

    let owner = AccountOwner::from_str(
        "0x02e900512d2fca22897f80a2f6932ff454f2752ef7afad18729dd25e5b5b6e00",
    )
    .unwrap();
    let chain_id =
        ChainId::from_str("aee928d4bf3880353b4a3cd9b6f88e6cc6e5ed050860abae439e7782e9b2dfe9")
            .unwrap();
    let creator = Account { chain_id, owner };

    let meme_1 =
        ApplicationId::from_str("b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bad")
            .unwrap();

    let response = swap
        .execute_operation(SwapOperation::InitializeLiquidity {
            creator,
            token_0_creator_chain_id: ChainId::from_str(
                "aee928d4bf3880353b4a3cd9b6f88e6cc6e5ed050860abae439e7782e9b2dfe8",
            )
            .unwrap(),
            token_0: meme_1,
            amount_0: Amount::ONE,
            amount_1: Amount::ONE,
            virtual_liquidity: false,
            to: None,
        })
        .await;

    assert!(matches!(response, SwapResponse::Ok));
}

#[tokio::test(flavor = "multi_thread")]
async fn operation_create_pool() {
    let mut swap = create_and_instantiate_swap();

    let meme_1 =
        ApplicationId::from_str("b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bad")
            .unwrap();
    let meme_2 =
        ApplicationId::from_str("b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bae")
            .unwrap();
    let chain_id =
        ChainId::from_str("aee928d4bf3880353b4a3cd9b6f88e6cc6e5ed050860abae439e7782e9b2dfe9")
            .unwrap();

    let response = swap
        .execute_operation(SwapOperation::CreatePool {
            token_0_creator_chain_id: chain_id,
            token_0: meme_1,
            token_1_creator_chain_id: Some(chain_id),
            token_1: Some(meme_2),
            amount_0: Amount::ONE,
            amount_1: Amount::ONE,
            to: None,
        })
        .await;

    assert!(matches!(response, SwapResponse::Ok));
}

fn mock_application_call(
    _authenticated: bool,
    _application_id: ApplicationId,
    _operation: Vec<u8>,
) -> Vec<u8> {
    bcs::to_bytes(&MemeResponse::ChainId(
        ChainId::from_str("aee928d4bf3880353b4a3cd9b6f88e6cc6e5ed050860abae439e7782e9b2dfe8")
            .unwrap(),
    ))
    .unwrap()
}

fn create_and_instantiate_swap() -> SwapContract {
    let owner = AccountOwner::from_str(
        "0x02e900512d2fca22897f80a2f6932ff454f2752ef7afad18729dd25e5b5b6e00",
    )
    .unwrap();
    let application_id =
        ApplicationId::from_str("b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5baf")
            .unwrap()
            .with_abi::<SwapAbi>();
    let meme_1 =
        ApplicationId::from_str("b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bad")
            .unwrap();
    let meme_1_chain_id =
        ChainId::from_str("aee928d4bf3880353b4a3cd9b6f88e6cc6e5ed050860abae439e7782e9b2dfe8")
            .unwrap();
    let chain_id =
        ChainId::from_str("aee928d4bf3880353b4a3cd9b6f88e6cc6e5ed050860abae439e7782e9b2dfe9")
            .unwrap();

    let mut runtime = ContractRuntime::new()
        .with_application_parameters(SwapParameters {})
        .with_application_id(application_id)
        .with_authenticated_signer(owner)
        .with_authenticated_caller_id(meme_1)
        .with_chain_id(meme_1_chain_id)
        .with_application_creator_chain_id(chain_id)
        .with_call_application_handler(mock_application_call)
        .with_owner_balance(owner, Amount::from_tokens(10000))
        .with_owner_balance(
            AccountOwner::from(application_id.forget_abi()),
            Amount::from_tokens(10000),
        )
        .with_chain_balance(Amount::from_tokens(10000))
        .with_chain_ownership(ChainOwnership::single(owner));

    let permissions = ApplicationPermissions {
        execute_operations: Some(vec![meme_1, application_id.forget_abi()]),
        mandatory_applications: vec![],
        close_chain: vec![application_id.forget_abi()],
        change_application_permissions: vec![application_id.forget_abi()],
        call_service_as_oracle: Some(vec![application_id.forget_abi()]),
        make_http_requests: Some(vec![application_id.forget_abi()]),
    };

    runtime.add_expected_open_chain_call(
        ChainOwnership::single(owner),
        permissions,
        Amount::from_tokens(1),
        chain_id,
    );

    let mut contract = SwapContract {
        state: Rc::new(RefCell::new(
            SwapState::load(runtime.root_view_storage_context())
                .blocking_wait()
                .expect("Failed to read from mock key value store"),
        )),
        runtime: Rc::new(RefCell::new(runtime)),
    };

    let bytecode_id = ModuleId::from_str("b94e486abcfc016e937dad4297523060095f405530c95d498d981a94141589f167693295a14c3b48460ad6f75d67d2414428227550eb8cee8ecaa37e8646518300").unwrap();
    contract
        .instantiate(InstantiationArgument {
            pool_bytecode_id: bytecode_id,
        })
        .now_or_never()
        .expect("Initialization of swap state should not await anything");

    contract
}
