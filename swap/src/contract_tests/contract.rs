use super::super::{SwapContract, SwapState};

use abi::{
    meme::MemeResponse,
    swap::{
        router::{
            InstantiationArgument, SwapAbi, SwapMessage, SwapOperation, SwapParameters,
            SwapResponse,
        },
        transaction::{Transaction, TransactionType},
    },
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
use swap::interfaces::state::StateInterface;

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

#[tokio::test(flavor = "multi_thread")]
async fn operation_create_pool_rejects_same_token_pair() {
    let mut swap = create_and_instantiate_swap();
    let meme_1 =
        ApplicationId::from_str("b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bad")
            .unwrap();
    let chain_id =
        ChainId::from_str("aee928d4bf3880353b4a3cd9b6f88e6cc6e5ed050860abae439e7782e9b2dfe9")
            .unwrap();

    let result = std::panic::AssertUnwindSafe(swap.execute_operation(SwapOperation::CreatePool {
        token_0_creator_chain_id: chain_id,
        token_0: meme_1,
        token_1_creator_chain_id: Some(chain_id),
        token_1: Some(meme_1),
        amount_0: Amount::ONE,
        amount_1: Amount::ONE,
        to: None,
    }))
    .catch_unwind()
    .await;

    assert!(result.is_err());
}

#[tokio::test(flavor = "multi_thread")]
async fn message_update_pool_duplicate_transaction_does_not_override_metadata() {
    let mut swap = create_and_instantiate_swap();
    let (token_0, token_1) = create_pool_for_update_tests(&mut swap).await;
    let owner = authenticated_account(&swap);

    let transaction = pool_transaction(100, owner, 10);
    swap.execute_message(SwapMessage::UpdatePool {
        token_0,
        token_1,
        transaction,
        token_0_price: Amount::from_str("1.5").unwrap(),
        token_1_price: Amount::from_str("0.66").unwrap(),
        reserve_0: Amount::from_tokens(100),
        reserve_1: Amount::from_tokens(200),
    })
    .await;

    swap.execute_message(SwapMessage::UpdatePool {
        token_0,
        token_1,
        transaction,
        token_0_price: Amount::from_str("9.9").unwrap(),
        token_1_price: Amount::from_str("0.11").unwrap(),
        reserve_0: Amount::from_tokens(900),
        reserve_1: Amount::from_tokens(901),
    })
    .await;

    let pool = swap
        .state
        .borrow()
        .get_pool(token_0, token_1)
        .await
        .unwrap()
        .unwrap();
    assert_eq!(pool.latest_transaction, Some(transaction));
    assert_eq!(pool.token_0_price, Some(Amount::from_str("1.5").unwrap()));
    assert_eq!(pool.token_1_price, Some(Amount::from_str("0.66").unwrap()));
    assert_eq!(pool.reserve_0, Some(Amount::from_tokens(100)));
    assert_eq!(pool.reserve_1, Some(Amount::from_tokens(200)));
}

#[tokio::test(flavor = "multi_thread")]
async fn message_update_pool_older_transaction_does_not_roll_back_state() {
    let mut swap = create_and_instantiate_swap();
    let (token_0, token_1) = create_pool_for_update_tests(&mut swap).await;
    let owner = authenticated_account(&swap);

    let older = pool_transaction(100, owner, 10);
    let newer = pool_transaction(101, owner, 11);

    swap.execute_message(SwapMessage::UpdatePool {
        token_0,
        token_1,
        transaction: newer,
        token_0_price: Amount::from_str("2.0").unwrap(),
        token_1_price: Amount::from_str("0.5").unwrap(),
        reserve_0: Amount::from_tokens(120),
        reserve_1: Amount::from_tokens(240),
    })
    .await;

    swap.execute_message(SwapMessage::UpdatePool {
        token_0,
        token_1,
        transaction: older,
        token_0_price: Amount::from_str("1.0").unwrap(),
        token_1_price: Amount::from_str("1.0").unwrap(),
        reserve_0: Amount::from_tokens(80),
        reserve_1: Amount::from_tokens(160),
    })
    .await;

    let pool = swap
        .state
        .borrow()
        .get_pool(token_0, token_1)
        .await
        .unwrap()
        .unwrap();
    assert_eq!(pool.latest_transaction, Some(newer));
    assert_eq!(pool.token_0_price, Some(Amount::from_str("2.0").unwrap()));
    assert_eq!(pool.token_1_price, Some(Amount::from_str("0.5").unwrap()));
    assert_eq!(pool.reserve_0, Some(Amount::from_tokens(120)));
    assert_eq!(pool.reserve_1, Some(Amount::from_tokens(240)));
}

#[tokio::test(flavor = "multi_thread")]
async fn message_update_pool_newer_transaction_advances_state() {
    let mut swap = create_and_instantiate_swap();
    let (token_0, token_1) = create_pool_for_update_tests(&mut swap).await;
    let owner = authenticated_account(&swap);

    let older = pool_transaction(100, owner, 10);
    let newer = pool_transaction(101, owner, 11);

    swap.execute_message(SwapMessage::UpdatePool {
        token_0,
        token_1,
        transaction: older,
        token_0_price: Amount::from_str("1.0").unwrap(),
        token_1_price: Amount::from_str("1.0").unwrap(),
        reserve_0: Amount::from_tokens(80),
        reserve_1: Amount::from_tokens(160),
    })
    .await;

    swap.execute_message(SwapMessage::UpdatePool {
        token_0,
        token_1,
        transaction: newer,
        token_0_price: Amount::from_str("2.0").unwrap(),
        token_1_price: Amount::from_str("0.5").unwrap(),
        reserve_0: Amount::from_tokens(120),
        reserve_1: Amount::from_tokens(240),
    })
    .await;

    let pool = swap
        .state
        .borrow()
        .get_pool(token_0, token_1)
        .await
        .unwrap()
        .unwrap();
    assert_eq!(pool.latest_transaction, Some(newer));
    assert_eq!(pool.token_0_price, Some(Amount::from_str("2.0").unwrap()));
    assert_eq!(pool.token_1_price, Some(Amount::from_str("0.5").unwrap()));
    assert_eq!(pool.reserve_0, Some(Amount::from_tokens(120)));
    assert_eq!(pool.reserve_1, Some(Amount::from_tokens(240)));
}

#[tokio::test(flavor = "multi_thread")]
async fn message_create_user_pool_rejects_duplicate_existing_pool() {
    let mut swap = create_and_instantiate_swap();
    let (token_0, token_1) = create_pool_for_update_tests(&mut swap).await;

    let result = std::panic::AssertUnwindSafe(
        swap.execute_message(SwapMessage::CreateUserPool {
            token_0_creator_chain_id: ChainId::from_str(
                "aee928d4bf3880353b4a3cd9b6f88e6cc6e5ed050860abae439e7782e9b2dfe8",
            )
            .unwrap(),
            token_0,
            token_1_creator_chain_id: Some(
                ChainId::from_str(
                    "aee928d4bf3880353b4a3cd9b6f88e6cc6e5ed050860abae439e7782e9b2dfe8",
                )
                .unwrap(),
            ),
            token_1,
            amount_0: Amount::ONE,
            amount_1: Amount::ONE,
            to: None,
        }),
    )
    .catch_unwind()
    .await;

    assert!(result.is_err());
}

#[tokio::test(flavor = "multi_thread")]
async fn message_pool_created_ignores_wrong_chain_receipt() {
    let mut swap = create_and_instantiate_swap();
    let creator = authenticated_account(&swap);
    let token_0 =
        ApplicationId::from_str("b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bad")
            .unwrap();
    let token_1 =
        ApplicationId::from_str("b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bae")
            .unwrap();
    let pool_application = Account {
        chain_id: ChainId::from_str(
            "aee928d4bf3880353b4a3cd9b6f88e6cc6e5ed050860abae439e7782e9b2dfea",
        )
        .unwrap(),
        owner: AccountOwner::from(
            ApplicationId::from_str(
                "b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bb1",
            )
            .unwrap(),
        ),
    };

    swap.execute_message(SwapMessage::PoolCreated {
        creator,
        pool_application,
        token_0,
        token_1: Some(token_1),
        amount_0: Amount::ONE,
        amount_1: Amount::ONE,
        virtual_initial_liquidity: false,
        to: None,
        user_pool: false,
    })
    .await;

    assert!(swap
        .state
        .borrow()
        .get_pool(token_0, Some(token_1))
        .await
        .unwrap()
        .is_none());
    assert_eq!(*swap.state.borrow().pool_id.get(), 1000);
}

#[tokio::test(flavor = "multi_thread")]
async fn message_pool_created_ignores_duplicate_receipt() {
    let mut swap = create_and_instantiate_swap();
    let creator = authenticated_account(&swap);
    let token_0 =
        ApplicationId::from_str("b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bad")
            .unwrap();
    let token_1 =
        ApplicationId::from_str("b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bae")
            .unwrap();
    let pool_chain_id =
        ChainId::from_str("aee928d4bf3880353b4a3cd9b6f88e6cc6e5ed050860abae439e7782e9b2dfea")
            .unwrap();
    let pool_application = Account {
        chain_id: pool_chain_id,
        owner: AccountOwner::from(
            ApplicationId::from_str(
                "b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bb2",
            )
            .unwrap(),
        ),
    };
    swap.state
        .borrow_mut()
        .create_pool_chain(pool_chain_id)
        .unwrap();

    let message = SwapMessage::PoolCreated {
        creator,
        pool_application,
        token_0,
        token_1: Some(token_1),
        amount_0: Amount::ONE,
        amount_1: Amount::ONE,
        virtual_initial_liquidity: false,
        to: None,
        user_pool: false,
    };

    swap.execute_message(message.clone()).await;
    assert_eq!(*swap.state.borrow().pool_id.get(), 1001);
    swap.execute_message(message).await;

    let pool = swap
        .state
        .borrow()
        .get_pool(token_0, Some(token_1))
        .await
        .unwrap()
        .unwrap();
    assert_eq!(pool.pool_application, pool_application);
    assert_eq!(*swap.state.borrow().pool_id.get(), 1001);
}

#[tokio::test(flavor = "multi_thread")]
async fn message_user_pool_created_is_idempotent() {
    let call_count = Rc::new(RefCell::new(0usize));
    let mut swap = create_and_instantiate_swap_with_call_handler({
        let call_count = call_count.clone();
        move |_authenticated, _application_id, _operation| {
            *call_count.borrow_mut() += 1;
            bcs::to_bytes(&MemeResponse::Ok).unwrap()
        }
    });
    let pool_application = Account {
        chain_id: ChainId::from_str(
            "aee928d4bf3880353b4a3cd9b6f88e6cc6e5ed050860abae439e7782e9b2dfea",
        )
        .unwrap(),
        owner: AccountOwner::from(
            ApplicationId::from_str(
                "b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bb3",
            )
            .unwrap(),
        ),
    };
    let token_0 =
        ApplicationId::from_str("b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bad")
            .unwrap();
    let token_1 =
        ApplicationId::from_str("b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bae")
            .unwrap();
    let message = SwapMessage::UserPoolCreated {
        pool_application,
        token_0,
        token_1: Some(token_1),
        amount_0: Amount::ONE,
        amount_1: Amount::ONE,
        to: None,
    };

    swap.execute_message(message.clone()).await;
    swap.execute_message(message).await;

    assert_eq!(*call_count.borrow(), 1);
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

fn authenticated_account(swap: &SwapContract) -> Account {
    let mut runtime = swap.runtime.borrow_mut();
    Account {
        chain_id: runtime.chain_id(),
        owner: runtime.authenticated_signer().unwrap(),
    }
}

fn pool_transaction(transaction_id: u32, from: Account, created_at: u64) -> Transaction {
    Transaction {
        transaction_id: Some(transaction_id),
        transaction_type: TransactionType::AddLiquidity,
        from,
        amount_0_in: Some(Amount::ONE),
        amount_0_out: None,
        amount_1_in: Some(Amount::ONE),
        amount_1_out: None,
        liquidity: Some(Amount::ONE),
        created_at: created_at.into(),
    }
}

async fn create_pool_for_update_tests(
    swap: &mut SwapContract,
) -> (ApplicationId, Option<ApplicationId>) {
    let token_0 =
        ApplicationId::from_str("b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bad")
            .unwrap();
    let token_1 =
        ApplicationId::from_str("b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bae")
            .unwrap();
    let creator = authenticated_account(swap);
    let pool_application = Account {
        chain_id: creator.chain_id,
        owner: AccountOwner::from(
            ApplicationId::from_str(
                "b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bb0",
            )
            .unwrap(),
        ),
    };

    swap.state
        .borrow_mut()
        .create_pool(creator, token_0, Some(token_1), pool_application, 1.into())
        .await
        .unwrap();

    (token_0, Some(token_1))
}

fn create_and_instantiate_swap() -> SwapContract {
    create_and_instantiate_swap_with_call_handler(mock_application_call)
}

fn create_and_instantiate_swap_with_call_handler<F>(handler: F) -> SwapContract
where
    F: FnMut(bool, ApplicationId, Vec<u8>) -> Vec<u8> + 'static,
{
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
        .with_system_time(0.into())
        .with_call_application_handler(handler)
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
