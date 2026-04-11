use super::super::{PoolContract, PoolState};

use abi::{
    meme::{MemeOperation, MemeResponse},
    swap::pool::{
        InstantiationArgument, PoolAbi, PoolMessage, PoolOperation, PoolParameters, PoolResponse,
    },
    swap::transaction::{Transaction, TransactionType},
};
use futures::FutureExt as _;
use linera_sdk::{
    bcs,
    linera_base_types::{Account, AccountOwner, Amount, ApplicationId, ChainId},
    util::BlockingWait,
    views::View,
    Contract, ContractRuntime,
};
use pool::{
    interfaces::{parameters::ParametersInterface, state::StateInterface},
    FundRequest, FundStatus, FundType,
};
use runtime::{
    contract::ContractRuntimeAdapter,
    interfaces::{base::BaseRuntimeContext, contract::ContractRuntimeContext},
};
use std::str::FromStr;
use std::{cell::RefCell, rc::Rc};

#[tokio::test(flavor = "multi_thread")]
async fn create_pool_with_real_liquidity() {
    let pool = create_and_instantiate_pool(false).await;
    let _ = pool.state.borrow().pool();
}

#[tokio::test(flavor = "multi_thread")]
async fn create_pool_with_virtual_liquidity() {
    let pool = create_and_instantiate_pool(true).await;
    let _ = pool.state.borrow().pool();
}

#[tokio::test(flavor = "multi_thread")]
async fn operation_swap() {
    let mut pool = create_and_instantiate_pool(true).await;

    let response = pool
        .execute_operation(PoolOperation::Swap {
            amount_0_in: None,
            amount_1_in: Some(Amount::ONE),
            amount_0_out_min: None,
            amount_1_out_min: None,
            to: None,
            block_timestamp: None,
        })
        .now_or_never()
        .expect("Execution of meme operation should not await anything");

    assert!(matches!(response, PoolResponse::Ok));
}

#[tokio::test(flavor = "multi_thread")]
async fn operation_add_liquidity() {
    let mut pool = create_and_instantiate_pool(true).await;

    let response = pool
        .execute_operation(PoolOperation::AddLiquidity {
            amount_0_in: Amount::ONE,
            amount_1_in: Amount::from_tokens(20),
            amount_0_out_min: None,
            amount_1_out_min: None,
            to: None,
            block_timestamp: None,
        })
        .now_or_never()
        .expect("Execution of meme operation should not await anything");

    assert!(matches!(response, PoolResponse::Ok));
}

#[tokio::test(flavor = "multi_thread")]
async fn message_set_fee_to_updates_fee_receiver_for_current_fee_to_setter() {
    let mut pool = create_and_instantiate_pool(true).await;
    let operator = authenticated_account(&pool);
    let account = Account {
        chain_id: operator.chain_id,
        owner: AccountOwner::from_str(
            "0x8b0f4d4320f64d5cf5fd742f5a7d6a51a8c3dbd9d6c6c23f73e3b0f8fbb04f11",
        )
        .unwrap(),
    };

    pool.execute_message(PoolMessage::SetFeeTo { operator, account })
        .await;

    let pool_state = pool.state.borrow().pool();
    assert_eq!(pool_state.fee_to, account);
    assert_eq!(pool_state.fee_to_setter, operator);
}

#[tokio::test(flavor = "multi_thread")]
async fn message_set_fee_to_setter_rotates_operator_and_invalidates_old_operator() {
    let mut pool = create_and_instantiate_pool(true).await;
    let old_operator = authenticated_account(&pool);
    let new_operator = Account {
        chain_id: old_operator.chain_id,
        owner: AccountOwner::from_str(
            "0x3f3c6f7fbc833f18d48f3b9d8552cf16e491061b85d34ed2a5b3720d9f2f4c31",
        )
        .unwrap(),
    };
    let target_fee_to = Account {
        chain_id: old_operator.chain_id,
        owner: AccountOwner::from_str(
            "0x3447565f8a4f3db39c46fc92f6fa5700d6c74a585cd49007daa4619052f5e91b",
        )
        .unwrap(),
    };

    pool.execute_message(PoolMessage::SetFeeToSetter {
        operator: old_operator,
        account: new_operator,
    })
    .await;
    assert_eq!(pool.state.borrow().pool().fee_to_setter, new_operator);

    let old_operator_attempt =
        std::panic::AssertUnwindSafe(pool.execute_message(PoolMessage::SetFeeTo {
            operator: old_operator,
            account: target_fee_to,
        }))
        .catch_unwind()
        .await;
    assert!(old_operator_attempt.is_err());

    pool.execute_message(PoolMessage::SetFeeTo {
        operator: new_operator,
        account: target_fee_to,
    })
    .await;

    let pool_state = pool.state.borrow().pool();
    assert_eq!(pool_state.fee_to_setter, new_operator);
    assert_eq!(pool_state.fee_to, target_fee_to);
}

#[tokio::test(flavor = "multi_thread")]
async fn message_set_fee_to_rejects_non_operator() {
    let mut pool = create_and_instantiate_pool(true).await;
    let current_operator = authenticated_account(&pool);
    let invalid_operator = Account {
        chain_id: current_operator.chain_id,
        owner: AccountOwner::from_str(
            "0x61f6a31f937dfb8a5e47f6d471b1e40f949e8ddfb66914318e403d315f0dce21",
        )
        .unwrap(),
    };
    let target_fee_to = Account {
        chain_id: current_operator.chain_id,
        owner: AccountOwner::from_str(
            "0x216bd78c27e4abfef4e1a6b4af2f14f4dd35df621d8f21891cf9d33d6535f1a1",
        )
        .unwrap(),
    };

    let result = std::panic::AssertUnwindSafe(pool.execute_message(PoolMessage::SetFeeTo {
        operator: invalid_operator,
        account: target_fee_to,
    }))
    .catch_unwind()
    .await;

    assert!(result.is_err());
    let pool_state = pool.state.borrow().pool();
    assert_eq!(pool_state.fee_to_setter, current_operator);
    assert_eq!(pool_state.fee_to, current_operator);
}

#[tokio::test(flavor = "multi_thread")]
async fn message_request_fund() {
    let mut pool = create_and_instantiate_pool(true).await;
    let token_0 = pool.state.borrow_mut().pool().token_0;

    pool.execute_message(PoolMessage::RequestFund {
        token: token_0,
        transfer_id: 1000,
        amount: Amount::ONE,
    })
    .await;
}

#[tokio::test(flavor = "multi_thread")]
async fn message_fund_success() {
    let mut pool = create_and_instantiate_pool(true).await;
    let mut runtime_context = ContractRuntimeAdapter::new(pool.runtime.clone());

    let owner = Account {
        chain_id: runtime_context.chain_id(),
        owner: runtime_context.authenticated_signer().unwrap(),
    };

    let fund_request = FundRequest {
        from: owner,
        token: Some(runtime_context.token_0()),
        amount_in: Amount::ONE,
        pair_token_amount_out_min: None,
        to: None,
        block_timestamp: None,
        fund_type: FundType::Swap,
        status: FundStatus::InFlight,
        error: None,
        prev_request: None,
        next_request: None,
    };

    let transfer_id = pool
        .state
        .borrow_mut()
        .create_fund_request(fund_request)
        .unwrap();
    pool.execute_message(PoolMessage::FundSuccess { transfer_id })
        .await;

    let fund_request = pool.state.borrow().fund_request(transfer_id).await.unwrap();
    assert_eq!(fund_request.status, FundStatus::Success);
}

#[tokio::test(flavor = "multi_thread")]
async fn message_fund_fail() {
    let mut pool = create_and_instantiate_pool(true).await;
    let mut runtime_context = ContractRuntimeAdapter::new(pool.runtime.clone());

    let owner = Account {
        chain_id: runtime_context.chain_id(),
        owner: runtime_context.authenticated_signer().unwrap(),
    };

    let fund_request = FundRequest {
        from: owner,
        token: Some(runtime_context.token_0()),
        amount_in: Amount::ONE,
        pair_token_amount_out_min: None,
        to: None,
        block_timestamp: None,
        fund_type: FundType::Swap,
        status: FundStatus::InFlight,
        error: None,
        prev_request: None,
        next_request: None,
    };

    let transfer_id = pool
        .state
        .borrow_mut()
        .create_fund_request(fund_request)
        .unwrap();
    pool.execute_message(PoolMessage::FundFail {
        transfer_id,
        error: "Error".to_string(),
    })
    .await;

    let fund_request = pool.state.borrow().fund_request(transfer_id).await.unwrap();
    assert_eq!(fund_request.status, FundStatus::Fail);
    assert_eq!(fund_request.error, Some("Error".to_string()));
}

#[tokio::test(flavor = "multi_thread")]
async fn message_swap() {
    let mut pool = create_and_instantiate_pool(true).await;
    let mut runtime_context = ContractRuntimeAdapter::new(pool.runtime.clone());

    let owner = Account {
        chain_id: runtime_context.chain_id(),
        owner: runtime_context.authenticated_signer().unwrap(),
    };

    let reserve_0 = pool.state.borrow().reserve_0();
    let reserve_1 = pool.state.borrow().reserve_1();
    let swap_amount_0 = pool
        .state
        .borrow()
        .calculate_swap_amount_0(Amount::ONE)
        .unwrap();

    pool.execute_message(PoolMessage::Swap {
        origin: owner,
        amount_0_in: None,
        amount_1_in: Some(Amount::ONE),
        amount_0_out_min: None,
        amount_1_out_min: None,
        to: None,
        block_timestamp: None,
    })
    .await;

    assert_eq!(
        reserve_0.try_sub(swap_amount_0).unwrap(),
        pool.state.borrow().reserve_0()
    );
    assert_eq!(
        reserve_1.try_add(Amount::ONE).unwrap(),
        pool.state.borrow().reserve_1()
    );
}

#[tokio::test(flavor = "multi_thread")]
async fn message_swap_min_amount_boundary() {
    let mut pool = create_and_instantiate_pool(true).await;
    let owner = authenticated_account(&pool);
    let amount_1_in = Amount::ONE;
    let exact_amount_0_out = pool
        .state
        .borrow()
        .calculate_swap_amount_0(amount_1_in)
        .unwrap();

    pool.execute_message(PoolMessage::Swap {
        origin: owner,
        amount_0_in: None,
        amount_1_in: Some(amount_1_in),
        amount_0_out_min: Some(exact_amount_0_out),
        amount_1_out_min: None,
        to: None,
        block_timestamp: None,
    })
    .await;

    let mut pool = create_and_instantiate_pool(true).await;
    let owner = authenticated_account(&pool);
    let reserve_0 = pool.state.borrow().reserve_0();
    let reserve_1 = pool.state.borrow().reserve_1();
    let transactions_before = pool
        .state
        .borrow()
        .latest_transactions
        .elements()
        .await
        .unwrap()
        .len();
    pool.execute_message(PoolMessage::Swap {
        origin: owner,
        amount_0_in: None,
        amount_1_in: Some(amount_1_in),
        amount_0_out_min: Some(exact_amount_0_out.try_add(Amount::from_attos(1)).unwrap()),
        amount_1_out_min: None,
        to: None,
        block_timestamp: None,
    })
    .await;
    assert_eq!(pool.state.borrow().reserve_0(), reserve_0);
    assert_eq!(pool.state.borrow().reserve_1(), reserve_1);
    assert_eq!(
        pool.state
            .borrow()
            .latest_transactions
            .elements()
            .await
            .unwrap()
            .len(),
        transactions_before
    );
}

#[tokio::test(flavor = "multi_thread")]
async fn message_add_liquidity() {
    let mut pool = create_and_instantiate_pool(true).await;
    let mut runtime_context = ContractRuntimeAdapter::new(pool.runtime.clone());

    let owner = Account {
        chain_id: runtime_context.chain_id(),
        owner: runtime_context.authenticated_signer().unwrap(),
    };

    pool.execute_message(PoolMessage::AddLiquidity {
        origin: owner,
        amount_0_in: Amount::ONE,
        amount_1_in: Amount::from_tokens(10),
        amount_0_out_min: None,
        amount_1_out_min: None,
        to: None,
        block_timestamp: None,
    })
    .await;

    assert_eq!(
        pool.state.borrow().liquidity(owner).await.unwrap(),
        Amount::from_str("0.1").unwrap()
    );

    let add_liquidity = pool.state.borrow().build_transaction(
        owner,
        Some(Amount::ONE),
        Some(Amount::from_tokens(10)),
        None,
        None,
        Some(Amount::from_str("0.1").unwrap()),
        runtime_context.system_time(),
    );
    pool.execute_message(PoolMessage::NewTransaction {
        transaction: add_liquidity,
    })
    .await;

    let transactions = pool
        .state
        .borrow()
        .latest_transactions
        .elements()
        .await
        .unwrap();
    assert_eq!(transactions.len(), 1);
    assert_eq!(
        transactions[0].transaction_type,
        TransactionType::AddLiquidity
    );
    assert_eq!(transactions[0].from, owner);
    assert_eq!(
        transactions[0].liquidity,
        Some(Amount::from_str("0.1").unwrap())
    );

    let (amount_0_out, amount_1_out) = pool
        .state
        .borrow()
        .try_calculate_liquidity_amount_pair(Amount::from_str("0.05").unwrap(), None, None)
        .unwrap();

    pool.execute_message(PoolMessage::RemoveLiquidity {
        origin: owner,
        liquidity: Amount::from_str("0.05").unwrap(),
        amount_0_out_min: None,
        amount_1_out_min: None,
        to: None,
        block_timestamp: None,
    })
    .await;

    assert_eq!(
        pool.state.borrow().liquidity(owner).await.unwrap(),
        Amount::from_str("0.05").unwrap()
    );

    let remove_liquidity = pool.state.borrow().build_transaction(
        owner,
        None,
        None,
        Some(amount_0_out),
        Some(amount_1_out),
        Some(Amount::from_str("0.05").unwrap()),
        runtime_context.system_time(),
    );
    pool.execute_message(PoolMessage::NewTransaction {
        transaction: remove_liquidity,
    })
    .await;

    let transactions = pool
        .state
        .borrow()
        .latest_transactions
        .elements()
        .await
        .unwrap();
    assert_eq!(transactions.len(), 2);
    assert_eq!(
        transactions[1].transaction_type,
        TransactionType::RemoveLiquidity
    );
    assert_eq!(transactions[1].from, owner);
    assert_eq!(
        transactions[1].liquidity,
        Some(Amount::from_str("0.05").unwrap())
    );
}

#[tokio::test(flavor = "multi_thread")]
async fn message_add_liquidity_min_amount_boundary() {
    let mut pool = create_and_instantiate_pool(true).await;
    let owner = authenticated_account(&pool);
    let amount_0_in = Amount::ONE;
    let amount_1_in = Amount::ONE;
    let (_, exact_amount_1) = pool
        .state
        .borrow()
        .try_calculate_swap_amount_pair(amount_0_in, amount_1_in, None, None)
        .unwrap();

    pool.execute_message(PoolMessage::AddLiquidity {
        origin: owner,
        amount_0_in,
        amount_1_in,
        amount_0_out_min: None,
        amount_1_out_min: Some(exact_amount_1),
        to: None,
        block_timestamp: None,
    })
    .await;

    let mut pool = create_and_instantiate_pool(true).await;
    let owner = authenticated_account(&pool);
    let failing_result =
        std::panic::AssertUnwindSafe(pool.execute_message(PoolMessage::AddLiquidity {
            origin: owner,
            amount_0_in,
            amount_1_in,
            amount_0_out_min: None,
            amount_1_out_min: Some(exact_amount_1.try_add(Amount::from_attos(1)).unwrap()),
            to: None,
            block_timestamp: None,
        }))
        .catch_unwind()
        .await;
    assert!(failing_result.is_err());
}

#[tokio::test(flavor = "multi_thread")]
async fn message_remove_liquidity_min_amount_boundary() {
    let liquidity = Amount::from_str("0.05").unwrap();

    let mut pool = create_and_instantiate_pool(true).await;
    let owner = authenticated_account(&pool);
    pool.execute_message(PoolMessage::AddLiquidity {
        origin: owner,
        amount_0_in: Amount::ONE,
        amount_1_in: Amount::from_tokens(10),
        amount_0_out_min: None,
        amount_1_out_min: None,
        to: None,
        block_timestamp: None,
    })
    .await;
    let (exact_amount_0, exact_amount_1) = pool
        .state
        .borrow()
        .try_calculate_liquidity_amount_pair(liquidity, None, None)
        .unwrap();

    pool.execute_message(PoolMessage::RemoveLiquidity {
        origin: owner,
        liquidity,
        amount_0_out_min: Some(exact_amount_0),
        amount_1_out_min: Some(exact_amount_1),
        to: None,
        block_timestamp: None,
    })
    .await;

    let mut pool = create_and_instantiate_pool(true).await;
    let owner = authenticated_account(&pool);
    pool.execute_message(PoolMessage::AddLiquidity {
        origin: owner,
        amount_0_in: Amount::ONE,
        amount_1_in: Amount::from_tokens(10),
        amount_0_out_min: None,
        amount_1_out_min: None,
        to: None,
        block_timestamp: None,
    })
    .await;
    let failing_result =
        std::panic::AssertUnwindSafe(pool.execute_message(PoolMessage::RemoveLiquidity {
            origin: owner,
            liquidity,
            amount_0_out_min: Some(exact_amount_0.try_add(Amount::from_attos(1)).unwrap()),
            amount_1_out_min: Some(exact_amount_1),
            to: None,
            block_timestamp: None,
        }))
        .catch_unwind()
        .await;
    assert!(failing_result.is_err());
}

#[tokio::test(flavor = "multi_thread")]
async fn add_liquidity_fund_second_leg_fail_does_not_close_flow() {
    let mut pool = create_and_instantiate_pool(true).await;
    let mut runtime_context = ContractRuntimeAdapter::new(pool.runtime.clone());
    let owner = Account {
        chain_id: runtime_context.chain_id(),
        owner: runtime_context.authenticated_signer().unwrap(),
    };

    let response = pool
        .execute_operation(PoolOperation::AddLiquidity {
            amount_0_in: Amount::ONE,
            amount_1_in: Amount::from_tokens(10),
            amount_0_out_min: None,
            amount_1_out_min: None,
            to: None,
            block_timestamp: None,
        })
        .now_or_never()
        .expect("Execution of meme operation should not await anything");
    assert!(matches!(response, PoolResponse::Ok));

    pool.execute_message(PoolMessage::FundSuccess { transfer_id: 1000 })
        .await;
    pool.execute_message(PoolMessage::FundFail {
        transfer_id: 1001,
        error: "second leg failed".to_string(),
    })
    .await;

    let fund_request_0 = pool.state.borrow().fund_request(1000).await.unwrap();
    let fund_request_1 = pool.state.borrow().fund_request(1001).await.unwrap();
    assert_eq!(fund_request_0.status, FundStatus::Success);
    assert_eq!(fund_request_1.status, FundStatus::Fail);
    assert_eq!(fund_request_1.error, Some("second leg failed".to_string()));
    assert_eq!(
        pool.state.borrow().liquidity(owner).await.unwrap(),
        Amount::ZERO
    );
    assert_eq!(
        pool.state
            .borrow()
            .latest_transactions
            .elements()
            .await
            .unwrap()
            .len(),
        0
    );

    let runtime = pool.runtime.borrow();
    let requests = runtime.created_send_message_requests();
    let request_fund_transfer_ids: Vec<_> = requests
        .iter()
        .filter_map(|request| match request.message {
            PoolMessage::RequestFund { transfer_id, .. } => Some(transfer_id),
            _ => None,
        })
        .collect();
    assert_eq!(request_fund_transfer_ids, vec![1000, 1001]);
    assert!(!requests
        .iter()
        .any(|request| matches!(request.message, PoolMessage::AddLiquidity { .. })));
}

#[tokio::test(flavor = "multi_thread")]
async fn add_liquidity_fund_success_only_queues_follow_up_message() {
    let mut pool = create_and_instantiate_pool(true).await;
    let mut runtime_context = ContractRuntimeAdapter::new(pool.runtime.clone());
    let owner = Account {
        chain_id: runtime_context.chain_id(),
        owner: runtime_context.authenticated_signer().unwrap(),
    };

    let response = pool
        .execute_operation(PoolOperation::AddLiquidity {
            amount_0_in: Amount::ONE,
            amount_1_in: Amount::from_tokens(10),
            amount_0_out_min: None,
            amount_1_out_min: None,
            to: None,
            block_timestamp: None,
        })
        .now_or_never()
        .expect("Execution of meme operation should not await anything");
    assert!(matches!(response, PoolResponse::Ok));

    pool.execute_message(PoolMessage::FundSuccess { transfer_id: 1000 })
        .await;
    pool.execute_message(PoolMessage::FundSuccess { transfer_id: 1001 })
        .await;

    let fund_request_0 = pool.state.borrow().fund_request(1000).await.unwrap();
    let fund_request_1 = pool.state.borrow().fund_request(1001).await.unwrap();
    assert_eq!(fund_request_0.status, FundStatus::Success);
    assert_eq!(fund_request_1.status, FundStatus::Success);
    assert_eq!(
        pool.state.borrow().liquidity(owner).await.unwrap(),
        Amount::ZERO
    );
    assert_eq!(
        pool.state
            .borrow()
            .latest_transactions
            .elements()
            .await
            .unwrap()
            .len(),
        0
    );

    let runtime = pool.runtime.borrow();
    let requests = runtime.created_send_message_requests();
    let request_fund_transfer_ids: Vec<_> = requests
        .iter()
        .filter_map(|request| match request.message {
            PoolMessage::RequestFund { transfer_id, .. } => Some(transfer_id),
            _ => None,
        })
        .collect();
    assert_eq!(request_fund_transfer_ids, vec![1000, 1001]);
    let add_liquidity_messages: Vec<_> = requests
        .iter()
        .filter(|request| matches!(request.message, PoolMessage::AddLiquidity { origin, .. } if origin == owner))
        .collect();
    assert_eq!(add_liquidity_messages.len(), 1);
    assert_eq!(
        requests
            .iter()
            .filter(|request| matches!(request.message, PoolMessage::NewTransaction { .. }))
            .count(),
        1
    );
}

#[tokio::test(flavor = "multi_thread")]
async fn message_new_transaction_is_idempotent() {
    let mut pool = create_and_instantiate_pool(true).await;
    let owner = authenticated_account(&pool);
    let transaction = pool.state.borrow().build_transaction(
        owner,
        Some(Amount::ONE),
        None,
        None,
        Some(Amount::from_str("0.00997").unwrap()),
        None,
        1.into(),
    );

    pool.execute_message(PoolMessage::NewTransaction { transaction })
        .await;
    pool.execute_message(PoolMessage::NewTransaction { transaction })
        .await;

    let transactions = pool
        .state
        .borrow()
        .latest_transactions
        .elements()
        .await
        .unwrap();
    assert_eq!(transactions.len(), 1);
    assert_eq!(transactions[0].transaction_id, Some(1000));
    assert_eq!(transactions[0].from, owner);
}

#[tokio::test(flavor = "multi_thread")]
async fn message_new_transaction_queue_keeps_latest_5000() {
    let mut pool = create_and_instantiate_pool(true).await;
    let owner = authenticated_account(&pool);

    for index in 0..5001u64 {
        let transaction = Transaction {
            transaction_id: None,
            transaction_type: TransactionType::BuyToken0,
            from: owner,
            amount_0_in: None,
            amount_0_out: Some(Amount::from_attos(index as u128 + 1)),
            amount_1_in: Some(Amount::from_attos(index as u128 + 11)),
            amount_1_out: None,
            liquidity: None,
            created_at: (index + 1).into(),
        };
        pool.execute_message(PoolMessage::NewTransaction { transaction })
            .await;
    }

    let transactions = pool
        .state
        .borrow()
        .latest_transactions
        .elements()
        .await
        .unwrap();
    assert_eq!(transactions.len(), 5000);
    assert_eq!(transactions.first().unwrap().transaction_id, Some(1001));
    assert_eq!(transactions.first().unwrap().created_at, 2.into());
    assert_eq!(transactions.last().unwrap().transaction_id, Some(6000));
    assert_eq!(transactions.last().unwrap().created_at, 5001.into());
}

#[test]
fn cross_application_call() {}

fn mock_application_call(
    _authenticated: bool,
    _application_id: ApplicationId,
    operation: Vec<u8>,
) -> Vec<u8> {
    match bcs::from_bytes::<MemeOperation>(&operation) {
        Ok(MemeOperation::CreatorChainId) => bcs::to_bytes(&MemeResponse::ChainId(
            ChainId::from_str("aee928d4bf3880353b4a3cd9b6f88e6cc6e5ed050860abae439e7782e9b2dfe9")
                .unwrap(),
        ))
        .unwrap(),
        Ok(_) => bcs::to_bytes(&MemeResponse::Ok).unwrap(),
        Err(_) => bcs::to_bytes(&MemeResponse::Ok).unwrap(),
    }
}

fn authenticated_account(pool: &PoolContract) -> Account {
    let mut runtime_context = ContractRuntimeAdapter::new(pool.runtime.clone());
    Account {
        chain_id: runtime_context.chain_id(),
        owner: runtime_context.authenticated_signer().unwrap(),
    }
}

async fn create_and_instantiate_pool(virtual_initial_liquidity: bool) -> PoolContract {
    let _ = env_logger::builder().is_test(true).try_init();

    let token_0 =
        ApplicationId::from_str("b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bad")
            .unwrap();
    let token_1 =
        ApplicationId::from_str("b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bae")
            .unwrap();
    let router_application_id =
        ApplicationId::from_str("b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5baf")
            .unwrap();
    let chain_id =
        ChainId::from_str("aee928d4bf3880353b4a3cd9b6f88e6cc6e5ed050860abae439e7782e9b2dfe8")
            .unwrap();
    let application_id =
        ApplicationId::from_str("b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bbd")
            .unwrap()
            .with_abi::<PoolAbi>();
    let owner = AccountOwner::from_str(
        "0x5279b3ae14d3b38e14b65a74aefe44824ea88b25c7841836e9ec77d991a5bc7f",
    )
    .unwrap();
    let creator = Account { chain_id, owner };
    let mut runtime = ContractRuntime::new()
        .with_application_parameters(PoolParameters {
            creator,
            token_0,
            token_1: Some(token_1),
            virtual_initial_liquidity,
            token_0_creator_chain_id: chain_id,
            token_1_creator_chain_id: Some(chain_id),
        })
        .with_chain_id(chain_id)
        .with_application_id(application_id)
        .with_authenticated_caller_id(router_application_id)
        .with_call_application_handler(mock_application_call)
        .with_application_creator_chain_id(chain_id)
        .with_system_time(0.into())
        .with_authenticated_signer(owner);

    runtime.set_message_origin_chain_id(chain_id);

    let mut contract = PoolContract {
        state: Rc::new(RefCell::new(
            PoolState::load(runtime.root_view_storage_context())
                .blocking_wait()
                .expect("Failed to read from mock key value store"),
        )),
        runtime: Rc::new(RefCell::new(runtime)),
    };

    contract
        .instantiate(InstantiationArgument {
            amount_0: Amount::from_str("1000").unwrap(),
            amount_1: Amount::from_str("10").unwrap(),
            pool_fee_percent_mul_100: 30,
            protocol_fee_percent_mul_100: 5,
            router_application_id,
        })
        .await;

    contract
}
