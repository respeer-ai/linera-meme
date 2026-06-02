use super::super::{PoolContract, PoolState};

use abi::{
    meme::{
        MemeOperation, MemeResponse, TransferFromApplicationReceiptPayload,
        TransferFromApplicationReceiptPurpose,
    },
    meme_token::MemeToken,
    swap::pool::{
        AddLiquidityTransferReceipt, BootstrapPolicy, ClaimTransferReceipt, FundRequestExt,
        FundType as FundRequestExtType, InstantiationArgument, PoolAbi, PoolMessage, PoolOperation,
        PoolParameters, PoolResponse, SwapTransferReceipt,
    },
};
use futures::FutureExt as _;
use linera_sdk::{
    bcs,
    linera_base_types::{Account, AccountOwner, Amount, ApplicationId, ChainId},
    util::BlockingWait,
    views::View,
    Contract, ContractRuntime,
};
use pool::interfaces::{parameters::ParametersInterface, state::StateInterface};
use runtime::{
    contract::ContractRuntimeAdapter,
    interfaces::{base::BaseRuntimeContext, contract::ContractRuntimeContext},
};
use std::str::FromStr;
use std::{cell::RefCell, rc::Rc};

#[tokio::test(flavor = "multi_thread")]
async fn create_pool_with_real_liquidity() {
    let pool = create_and_instantiate_pool(false).await;
    assert_eq!(pool.state.borrow().reserve_0(), Amount::ZERO);
    assert_eq!(pool.state.borrow().reserve_1(), Amount::ZERO);
    assert_eq!(total_supply(&pool), Amount::ZERO);
}

#[tokio::test(flavor = "multi_thread")]
async fn create_pool_with_virtual_liquidity() {
    let pool = create_and_instantiate_pool(true).await;
    assert_eq!(pool.state.borrow().reserve_0(), Amount::ZERO);
    assert_eq!(pool.state.borrow().reserve_1(), Amount::ZERO);
    assert_eq!(total_supply(&pool), Amount::ZERO);
}

#[tokio::test(flavor = "multi_thread")]
async fn message_initialize_liquidity_writes_first_reserve_share_facts() {
    let mut pool = create_and_instantiate_pool(false).await;
    let origin = authenticated_account(&pool);

    pool.execute_message(PoolMessage::InitializeLiquidity {
        origin,
        amount_0_in: Amount::from_str("1000").unwrap(),
        amount_1_in: Amount::from_str("10").unwrap(),
        to: None,
        block_timestamp: None,
    })
    .await;

    assert_eq!(
        pool.state.borrow().reserve_0(),
        Amount::from_str("1000").unwrap()
    );
    assert_eq!(
        pool.state.borrow().reserve_1(),
        Amount::from_str("10").unwrap()
    );
    assert!(total_supply(&pool) > Amount::ZERO);
}

#[tokio::test(flavor = "multi_thread")]
async fn message_initialize_liquidity_rejects_user_create_pool_policy() {
    let mut pool = create_and_instantiate_user_pool().await;
    let origin = authenticated_account(&pool);

    let result =
        std::panic::AssertUnwindSafe(pool.execute_message(PoolMessage::InitializeLiquidity {
            origin,
            amount_0_in: Amount::from_str("1000").unwrap(),
            amount_1_in: Amount::from_str("10").unwrap(),
            to: None,
            block_timestamp: None,
        }))
        .catch_unwind()
        .await;

    assert!(result.is_err());
    assert_eq!(pool.state.borrow().reserve_0(), Amount::ZERO);
    assert_eq!(pool.state.borrow().reserve_1(), Amount::ZERO);
    assert_eq!(total_supply(&pool), Amount::ZERO);
}

#[tokio::test(flavor = "multi_thread")]
async fn operation_initialize_liquidity_requires_token0_caller_and_queues_finalize_message() {
    let mut pool = create_and_instantiate_native_pool(false).await;
    let token_0 = pool.runtime.borrow_mut().application_parameters().token_0;
    pool.runtime
        .borrow_mut()
        .set_authenticated_caller_id(token_0);

    let response = pool
        .execute_operation(PoolOperation::InitializeLiquidity {
            amount_0_in: Amount::from_tokens(1000),
            amount_1_in: Amount::from_tokens(10),
            to: None,
            block_timestamp: None,
        })
        .await;

    assert!(matches!(response, PoolResponse::Ok));
    assert_eq!(pool.state.borrow().reserve_0(), Amount::ZERO);
    assert_eq!(pool.state.borrow().reserve_1(), Amount::ZERO);

    let runtime = pool.runtime.borrow();
    let requests = runtime.created_send_message_requests();
    assert!(requests
        .iter()
        .all(|request| request.authenticated && !request.is_tracked));
    assert_eq!(
        requests
            .iter()
            .filter(|request| matches!(request.message, PoolMessage::InitializeLiquidity { .. }))
            .count(),
        1
    );
}

#[tokio::test(flavor = "multi_thread")]
async fn operation_initialize_liquidity_rejects_non_token0_caller() {
    let mut pool = create_and_instantiate_native_pool(false).await;

    let result =
        std::panic::AssertUnwindSafe(pool.execute_operation(PoolOperation::InitializeLiquidity {
            amount_0_in: Amount::from_tokens(1000),
            amount_1_in: Amount::from_tokens(10),
            to: None,
            block_timestamp: None,
        }))
        .catch_unwind()
        .await;

    assert!(result.is_err());
}

#[tokio::test(flavor = "multi_thread")]
async fn operation_swap() {
    let mut pool = create_and_initialize_pool(true).await;

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
async fn operation_swap_meme_input_queues_message_carried_funding_without_persisting_request() {
    let mut pool = create_and_initialize_pool(true).await;
    let origin = authenticated_account(&pool);
    let token_0 = pool.runtime.borrow_mut().application_parameters().token_0;
    let token_chain = mock_token_creator_chain_id();
    let message_count_before = pool.runtime.borrow().created_send_message_requests().len();

    let response = pool
        .execute_operation(PoolOperation::Swap {
            amount_0_in: Some(Amount::ONE),
            amount_1_in: None,
            amount_0_out_min: None,
            amount_1_out_min: Some(Amount::from_attos(1)),
            to: None,
            block_timestamp: None,
        })
        .await;

    assert!(matches!(response, PoolResponse::Ok));
    let runtime = pool.runtime.borrow();
    let requests = &runtime.created_send_message_requests()[message_count_before..];
    assert_eq!(requests.len(), 1);
    assert_eq!(requests[0].destination, token_chain);
    assert!(requests[0].authenticated);
    assert!(!requests[0].is_tracked);
    assert!(matches!(
        &requests[0].message,
        PoolMessage::RequestFundExt {
            prev: None,
            request,
            next: None,
        } if request.from == origin
            && request.token == Some(token_0)
            && request.amount_in == Amount::ONE
            && request.counterparty_amount_out_min == Some(Amount::from_attos(1))
            && request.fund_type == FundRequestExtType::Swap
    ));
}

#[tokio::test(flavor = "multi_thread")]
async fn message_swap_rejects_without_finalized_reserve_share_facts() {
    let mut pool = create_and_instantiate_pool_with_amounts(false).await;
    let origin = authenticated_account(&pool);
    let reserve_0_before = pool.state.borrow().reserve_0();
    let reserve_1_before = pool.state.borrow().reserve_1();
    let total_supply_before = total_supply(&pool);
    let request_count_before = pool.runtime.borrow().created_send_message_requests().len();

    let result = std::panic::AssertUnwindSafe(pool.execute_message(PoolMessage::Swap {
        origin,
        amount_0_in: Some(Amount::ONE),
        amount_1_in: None,
        amount_0_out_min: None,
        amount_1_out_min: None,
        to: None,
        block_timestamp: None,
    }))
    .catch_unwind()
    .await;

    assert!(result.is_err());
    assert_eq!(pool.state.borrow().reserve_0(), reserve_0_before);
    assert_eq!(pool.state.borrow().reserve_1(), reserve_1_before);
    assert_eq!(total_supply(&pool), total_supply_before);
    assert_eq!(
        pool.runtime.borrow().created_send_message_requests().len(),
        request_count_before
    );
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
async fn message_remove_liquidity_rejects_without_finalized_reserve_share_facts() {
    let mut pool = create_and_instantiate_pool_with_amounts(false).await;
    let origin = authenticated_account(&pool);
    let reserve_0_before = pool.state.borrow().reserve_0();
    let reserve_1_before = pool.state.borrow().reserve_1();
    let total_supply_before = total_supply(&pool);
    let request_count_before = pool.runtime.borrow().created_send_message_requests().len();

    let result = std::panic::AssertUnwindSafe(pool.execute_message(PoolMessage::RemoveLiquidity {
        origin,
        liquidity: Amount::ONE,
        amount_0_out_min: None,
        amount_1_out_min: None,
        to: None,
        block_timestamp: None,
    }))
    .catch_unwind()
    .await;

    assert!(result.is_err());
    assert_eq!(pool.state.borrow().reserve_0(), reserve_0_before);
    assert_eq!(pool.state.borrow().reserve_1(), reserve_1_before);
    assert_eq!(total_supply(&pool), total_supply_before);
    assert_eq!(
        pool.runtime.borrow().created_send_message_requests().len(),
        request_count_before
    );
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
async fn message_swap() {
    let mut pool = create_and_initialize_pool(true).await;
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
    assert_eq!(
        pool.state
            .borrow()
            .claimable_balance(MemeToken::Fungible(runtime_context.token_0()), owner)
            .await
            .unwrap(),
        swap_amount_0
    );
}

#[tokio::test(flavor = "multi_thread")]
async fn message_swap_min_amount_boundary() {
    let mut pool = create_and_initialize_pool(true).await;
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

    let mut pool = create_and_initialize_pool(true).await;
    let owner = authenticated_account(&pool);
    let reserve_0 = pool.state.borrow().reserve_0();
    let reserve_1 = pool.state.borrow().reserve_1();
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
}

#[tokio::test(flavor = "multi_thread")]
async fn message_add_liquidity() {
    let mut pool = create_and_initialize_pool(true).await;
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

    assert_eq!(
        pool.state.borrow().liquidity(owner).await.unwrap(),
        Amount::from_str("100.1").unwrap()
    );

    let (amount_0_out, amount_1_out) = pool
        .state
        .borrow()
        .try_calculate_liquidity_amount_pair(Amount::from_str("100.05").unwrap(), None, None)
        .unwrap();

    pool.execute_message(PoolMessage::RemoveLiquidity {
        origin: owner,
        liquidity: Amount::from_str("100.05").unwrap(),
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

    assert!(amount_0_out > Amount::ZERO);
    assert!(amount_1_out > Amount::ZERO);
}

#[tokio::test(flavor = "multi_thread")]
async fn message_add_liquidity_min_amount_boundary() {
    let mut pool = create_and_initialize_pool(true).await;
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

    let mut pool = create_and_initialize_pool(true).await;
    let owner = authenticated_account(&pool);
    pool.execute_message(PoolMessage::AddLiquidity {
        origin: owner,
        amount_0_in,
        amount_1_in,
        amount_0_out_min: None,
        amount_1_out_min: Some(exact_amount_1.try_add(Amount::from_attos(1)).unwrap()),
        to: None,
        block_timestamp: None,
    })
    .await;
    let parameters = pool.runtime.borrow_mut().application_parameters();
    assert_eq!(
        pool.state
            .borrow()
            .claimable_balance(MemeToken::Fungible(parameters.token_0), owner)
            .await
            .unwrap(),
        amount_0_in
    );
    assert_eq!(
        pool.state
            .borrow()
            .claimable_balance(MemeToken::from(parameters.token_1), owner)
            .await
            .unwrap(),
        amount_1_in
    );
}

#[tokio::test(flavor = "multi_thread")]
async fn message_remove_liquidity_min_amount_boundary() {
    let liquidity = Amount::from_str("0.05").unwrap();

    let mut pool = create_and_initialize_pool(true).await;
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

    let mut pool = create_and_initialize_pool(true).await;
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
async fn message_add_liquidity_mints_fee_to_after_swap_growth() {
    let mut pool = create_and_initialize_pool(false).await;
    let operator = authenticated_account(&pool);
    let fee_to = alternate_account(operator.chain_id);

    pool.execute_message(PoolMessage::SetFeeTo {
        operator,
        account: fee_to,
    })
    .await;

    pool.execute_message(PoolMessage::Swap {
        origin: operator,
        amount_0_in: None,
        amount_1_in: Some(Amount::ONE),
        amount_0_out_min: None,
        amount_1_out_min: None,
        to: None,
        block_timestamp: None,
    })
    .await;

    assert_eq!(
        pool.state.borrow().liquidity(fee_to).await.unwrap(),
        Amount::ZERO
    );

    pool.execute_message(PoolMessage::AddLiquidity {
        origin: operator,
        amount_0_in: Amount::ONE,
        amount_1_in: Amount::from_tokens(10),
        amount_0_out_min: None,
        amount_1_out_min: None,
        to: None,
        block_timestamp: None,
    })
    .await;

    assert!(pool.state.borrow().liquidity(fee_to).await.unwrap() > Amount::ZERO);
}

#[tokio::test(flavor = "multi_thread")]
async fn message_remove_liquidity_mints_fee_to_and_updates_reserves_after_swap_growth() {
    let mut pool = create_and_initialize_pool(false).await;
    let operator = authenticated_account(&pool);
    let fee_to = alternate_account(operator.chain_id);

    pool.execute_message(PoolMessage::SetFeeTo {
        operator,
        account: fee_to,
    })
    .await;

    pool.execute_message(PoolMessage::Swap {
        origin: operator,
        amount_0_in: None,
        amount_1_in: Some(Amount::ONE),
        amount_0_out_min: None,
        amount_1_out_min: None,
        to: None,
        block_timestamp: None,
    })
    .await;

    let reserve_0_before = pool.state.borrow().reserve_0();
    let reserve_1_before = pool.state.borrow().reserve_1();

    pool.execute_message(PoolMessage::RemoveLiquidity {
        origin: operator,
        liquidity: Amount::ONE,
        amount_0_out_min: None,
        amount_1_out_min: None,
        to: None,
        block_timestamp: None,
    })
    .await;

    assert!(pool.state.borrow().liquidity(fee_to).await.unwrap() > Amount::ZERO);
    assert!(pool.state.borrow().reserve_0() < reserve_0_before);
    assert!(pool.state.borrow().reserve_1() < reserve_1_before);
}

#[tokio::test(flavor = "multi_thread")]
async fn message_add_liquidity_conserves_total_supply_with_fee_dilution() {
    let mut pool = create_and_initialize_pool(false).await;
    let operator = authenticated_account(&pool);
    let fee_to = alternate_account(operator.chain_id);

    pool.execute_message(PoolMessage::SetFeeTo {
        operator,
        account: fee_to,
    })
    .await;

    pool.execute_message(PoolMessage::Swap {
        origin: operator,
        amount_0_in: None,
        amount_1_in: Some(Amount::ONE),
        amount_0_out_min: None,
        amount_1_out_min: None,
        to: None,
        block_timestamp: None,
    })
    .await;

    pool.execute_message(PoolMessage::AddLiquidity {
        origin: operator,
        amount_0_in: Amount::ONE,
        amount_1_in: Amount::from_tokens(10),
        amount_0_out_min: None,
        amount_1_out_min: None,
        to: None,
        block_timestamp: None,
    })
    .await;

    let fee_to_share = pool.state.borrow().liquidity(fee_to).await.unwrap();
    let operator_share = pool.state.borrow().liquidity(operator).await.unwrap();
    let total_supply = total_supply(&pool);

    assert_eq!(
        fee_to_share,
        Amount::from_str("0.002272933913650825").unwrap()
    );
    assert_eq!(
        operator_share,
        Amount::from_str("100.109972499545424841").unwrap(),
    );
    assert_eq!(
        total_supply,
        Amount::from_str("100.112245433459075666").unwrap()
    );
    assert_eq!(operator_share.try_add(fee_to_share).unwrap(), total_supply);
}

#[tokio::test(flavor = "multi_thread")]
async fn message_remove_liquidity_conserves_total_supply_after_fee_mint() {
    let mut pool = create_and_initialize_pool(false).await;
    let operator = authenticated_account(&pool);
    let fee_to = alternate_account(operator.chain_id);

    pool.execute_message(PoolMessage::SetFeeTo {
        operator,
        account: fee_to,
    })
    .await;

    pool.execute_message(PoolMessage::Swap {
        origin: operator,
        amount_0_in: None,
        amount_1_in: Some(Amount::ONE),
        amount_0_out_min: None,
        amount_1_out_min: None,
        to: None,
        block_timestamp: None,
    })
    .await;

    pool.execute_message(PoolMessage::RemoveLiquidity {
        origin: operator,
        liquidity: Amount::ONE,
        amount_0_out_min: None,
        amount_1_out_min: None,
        to: None,
        block_timestamp: None,
    })
    .await;

    let fee_to_share = pool.state.borrow().liquidity(fee_to).await.unwrap();
    let operator_share = pool.state.borrow().liquidity(operator).await.unwrap();
    let total_supply = total_supply(&pool);

    assert_eq!(
        fee_to_share,
        Amount::from_str("0.002272933913650825").unwrap()
    );
    assert_eq!(operator_share, Amount::from_str("99").unwrap());
    assert_eq!(
        total_supply,
        Amount::from_str("99.002272933913650825").unwrap()
    );
    assert_eq!(operator_share.try_add(fee_to_share).unwrap(), total_supply);
}

#[tokio::test(flavor = "multi_thread")]
async fn message_new_transaction_forwards_catalog_update_without_history_storage() {
    let mut pool = create_and_initialize_pool(true).await;
    let owner = authenticated_account(&pool);
    let transaction = pool.state.borrow_mut().build_transaction(
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

    assert_eq!(transaction.transaction_id, Some(1001));
}

#[tokio::test(flavor = "multi_thread")]
async fn operation_claim_forwards_to_pool_creator_chain_without_state_change() {
    let mut pool = create_and_instantiate_native_pool(false).await;
    let owner = authenticated_account(&pool);
    let user_chain_id =
        ChainId::from_str("bee928d4bf3880353b4a3cd9b6f88e6cc6e5ed050860abae439e7782e9b2dfe8")
            .unwrap();
    let creator_chain_id = pool.runtime.borrow_mut().application_creator_chain_id();
    let amount = Amount::from_tokens(5);

    pool.runtime.borrow_mut().set_chain_id(user_chain_id);
    pool.state
        .borrow_mut()
        .credit(
            MemeToken::Native,
            Account {
                chain_id: creator_chain_id,
                owner: owner.owner,
            },
            amount,
        )
        .await
        .unwrap();

    let response = pool
        .execute_operation(PoolOperation::Claim {
            token: None,
            amount,
        })
        .await;

    assert!(matches!(response, PoolResponse::Ok));
    assert_eq!(
        pool.state
            .borrow()
            .claimable_balance(
                MemeToken::Native,
                Account {
                    chain_id: creator_chain_id,
                    owner: owner.owner
                }
            )
            .await
            .unwrap(),
        amount
    );
    assert_eq!(
        pool.state
            .borrow()
            .claiming_balance(
                MemeToken::Native,
                Account {
                    chain_id: creator_chain_id,
                    owner: owner.owner
                }
            )
            .await
            .unwrap(),
        Amount::ZERO
    );

    let runtime = pool.runtime.borrow();
    let requests = runtime.created_send_message_requests();
    let request = requests.last().unwrap();
    assert_eq!(request.destination, creator_chain_id);
    assert!(request.authenticated);
    assert!(!request.is_tracked);
    assert!(matches!(
        &request.message,
        PoolMessage::Claim { origin, token, amount: claim_amount }
            if origin.chain_id == user_chain_id
                && origin.owner == owner.owner
                && token.is_none()
                && *claim_amount == amount
    ));
}

#[tokio::test(flavor = "multi_thread")]
async fn message_claim_native_transfers_and_completes_claiming() {
    let mut pool = create_and_instantiate_native_pool(false).await;
    let owner = authenticated_account(&pool);
    let amount = Amount::from_tokens(5);
    let application_owner =
        AccountOwner::from(pool.runtime.borrow_mut().application_id().forget_abi());

    pool.runtime
        .borrow_mut()
        .set_owner_balance(application_owner, amount);
    pool.runtime
        .borrow_mut()
        .set_owner_balance(owner.owner, Amount::ZERO);
    pool.state
        .borrow_mut()
        .credit(MemeToken::Native, owner, amount)
        .await
        .unwrap();

    pool.execute_message(PoolMessage::Claim {
        origin: owner,
        token: None,
        amount,
    })
    .await;

    assert_eq!(
        pool.state
            .borrow()
            .claimable_balance(MemeToken::Native, owner)
            .await
            .unwrap(),
        Amount::ZERO
    );
    assert_eq!(
        pool.state
            .borrow()
            .claiming_balance(MemeToken::Native, owner)
            .await
            .unwrap(),
        Amount::ZERO
    );
    assert_eq!(pool.runtime.borrow_mut().owner_balance(owner.owner), amount);
}

#[tokio::test(flavor = "multi_thread")]
async fn message_claim_fungible_moves_to_claiming() {
    let mut pool = create_and_instantiate_pool(false).await;
    let owner = authenticated_account(&pool);
    let token_0 = pool.runtime.borrow_mut().application_parameters().token_0;
    let token = MemeToken::Fungible(token_0);
    let amount = Amount::from_tokens(5);

    pool.state
        .borrow_mut()
        .credit(token, owner, amount)
        .await
        .unwrap();

    let captured = std::rc::Rc::new(std::cell::RefCell::new(None));
    let captured_for_handler = captured.clone();
    pool.runtime.borrow_mut().set_call_application_handler(
        move |_authenticated, application_id, operation| match bcs::from_bytes::<MemeOperation>(
            &operation,
        ) {
            Ok(MemeOperation::CreatorChainId) => {
                bcs::to_bytes(&MemeResponse::ChainId(mock_token_creator_chain_id())).unwrap()
            }
            _ => {
                *captured_for_handler.borrow_mut() = Some((application_id, operation));
                bcs::to_bytes(&MemeResponse::Ok).unwrap()
            }
        },
    );

    pool.execute_message(PoolMessage::Claim {
        origin: owner,
        token: Some(token_0),
        amount,
    })
    .await;

    let (application_id, operation) = captured.borrow().clone().unwrap();
    assert_eq!(application_id, token_0);
    assert!(matches!(
        bcs::from_bytes::<MemeOperation>(&operation).unwrap(),
        MemeOperation::TransferFromApplicationWithReceipt {
            to,
            amount: call_amount,
            receipt,
        } if to == owner
            && call_amount == amount
            && receipt.purpose == TransferFromApplicationReceiptPurpose::PoolClaim
            && receipt.owner == owner
            && receipt.token == token_0
            && receipt.amount == amount
            && receipt.result.is_none()
    ));
    assert_eq!(
        pool.state
            .borrow()
            .claimable_balance(token, owner)
            .await
            .unwrap(),
        Amount::ZERO
    );
    assert_eq!(
        pool.state
            .borrow()
            .claiming_balance(token, owner)
            .await
            .unwrap(),
        amount
    );
}

#[tokio::test(flavor = "multi_thread")]
async fn message_claim_fungible_pending_amount_cannot_be_claimed_again() {
    let mut pool = create_and_instantiate_pool(false).await;
    let owner = authenticated_account(&pool);
    let token_0 = pool.runtime.borrow_mut().application_parameters().token_0;
    let token = MemeToken::Fungible(token_0);
    let amount = Amount::from_tokens(5);

    pool.state
        .borrow_mut()
        .credit(token, owner, amount)
        .await
        .unwrap();
    pool.execute_message(PoolMessage::Claim {
        origin: owner,
        token: Some(token_0),
        amount,
    })
    .await;

    let result = std::panic::AssertUnwindSafe(pool.execute_message(PoolMessage::Claim {
        origin: owner,
        token: Some(token_0),
        amount,
    }))
    .catch_unwind()
    .await;

    assert!(result.is_err());
    assert_eq!(
        pool.state
            .borrow()
            .claimable_balance(token, owner)
            .await
            .unwrap(),
        Amount::ZERO
    );
    assert_eq!(
        pool.state
            .borrow()
            .claiming_balance(token, owner)
            .await
            .unwrap(),
        amount
    );
}

#[tokio::test(flavor = "multi_thread")]
async fn message_claim_native_rejects_meme_meme_pool() {
    let mut pool = create_and_instantiate_pool(false).await;
    let owner = authenticated_account(&pool);
    let amount = Amount::from_tokens(5);
    pool.state
        .borrow_mut()
        .credit(MemeToken::Native, owner, amount)
        .await
        .unwrap();

    let result = std::panic::AssertUnwindSafe(pool.execute_message(PoolMessage::Claim {
        origin: owner,
        token: None,
        amount,
    }))
    .catch_unwind()
    .await;

    assert!(result.is_err());
    assert_eq!(
        pool.state
            .borrow()
            .claimable_balance(MemeToken::Native, owner)
            .await
            .unwrap(),
        amount
    );
    assert_eq!(
        pool.state
            .borrow()
            .claiming_balance(MemeToken::Native, owner)
            .await
            .unwrap(),
        Amount::ZERO
    );
}

#[tokio::test(flavor = "multi_thread")]
async fn operation_claim_transfer_receipt_success_consumes_claiming() {
    let mut pool = create_and_instantiate_pool(false).await;
    let owner = authenticated_account(&pool);
    let token_0 = pool.runtime.borrow_mut().application_parameters().token_0;
    let token = MemeToken::Fungible(token_0);
    let amount = Amount::from_tokens(5);

    pool.runtime
        .borrow_mut()
        .set_authenticated_caller_id(token_0);
    pool.state
        .borrow_mut()
        .credit(token, owner, amount)
        .await
        .unwrap();
    pool.state
        .borrow_mut()
        .claim(token, owner, amount)
        .await
        .unwrap();

    let response = pool
        .execute_operation(PoolOperation::ClaimTransferReceipt {
            receipt: ClaimTransferReceipt {
                owner,
                token: token_0,
                amount,
                result: Ok(()),
            },
        })
        .await;

    assert!(matches!(response, PoolResponse::Ok));
    assert_eq!(
        pool.state
            .borrow()
            .claimable_balance(token, owner)
            .await
            .unwrap(),
        Amount::ZERO
    );
    assert_eq!(
        pool.state
            .borrow()
            .claiming_balance(token, owner)
            .await
            .unwrap(),
        Amount::ZERO
    );
}

#[tokio::test(flavor = "multi_thread")]
async fn operation_claim_transfer_receipt_rejects_duplicate_success_receipt() {
    let mut pool = create_and_instantiate_pool(false).await;
    let owner = authenticated_account(&pool);
    let token_0 = pool.runtime.borrow_mut().application_parameters().token_0;
    let token = MemeToken::Fungible(token_0);
    let amount = Amount::from_tokens(5);

    pool.runtime
        .borrow_mut()
        .set_authenticated_caller_id(token_0);
    pool.state
        .borrow_mut()
        .credit(token, owner, amount)
        .await
        .unwrap();
    pool.state
        .borrow_mut()
        .claim(token, owner, amount)
        .await
        .unwrap();

    pool.execute_operation(PoolOperation::ClaimTransferReceipt {
        receipt: ClaimTransferReceipt {
            owner,
            token: token_0,
            amount,
            result: Ok(()),
        },
    })
    .await;

    let result =
        std::panic::AssertUnwindSafe(pool.execute_operation(PoolOperation::ClaimTransferReceipt {
            receipt: ClaimTransferReceipt {
                owner,
                token: token_0,
                amount,
                result: Ok(()),
            },
        }))
        .catch_unwind()
        .await;

    assert!(result.is_err());
    assert_eq!(
        pool.state
            .borrow()
            .claimable_balance(token, owner)
            .await
            .unwrap(),
        Amount::ZERO
    );
    assert_eq!(
        pool.state
            .borrow()
            .claiming_balance(token, owner)
            .await
            .unwrap(),
        Amount::ZERO
    );
}

#[tokio::test(flavor = "multi_thread")]
async fn operation_claim_transfer_receipt_rejects_invalid_caller() {
    let mut pool = create_and_instantiate_pool(false).await;
    let owner = authenticated_account(&pool);
    let token_0 = pool.runtime.borrow_mut().application_parameters().token_0;
    let token_1 = pool
        .runtime
        .borrow_mut()
        .application_parameters()
        .token_1
        .unwrap();
    let token = MemeToken::Fungible(token_0);
    let amount = Amount::from_tokens(5);

    pool.runtime
        .borrow_mut()
        .set_authenticated_caller_id(token_1);
    pool.state
        .borrow_mut()
        .credit(token, owner, amount)
        .await
        .unwrap();
    pool.state
        .borrow_mut()
        .claim(token, owner, amount)
        .await
        .unwrap();

    let result =
        std::panic::AssertUnwindSafe(pool.execute_operation(PoolOperation::ClaimTransferReceipt {
            receipt: ClaimTransferReceipt {
                owner,
                token: token_0,
                amount,
                result: Ok(()),
            },
        }))
        .catch_unwind()
        .await;

    assert!(result.is_err());
    assert_eq!(
        pool.state
            .borrow()
            .claimable_balance(token, owner)
            .await
            .unwrap(),
        Amount::ZERO
    );
    assert_eq!(
        pool.state
            .borrow()
            .claiming_balance(token, owner)
            .await
            .unwrap(),
        amount
    );
}

#[tokio::test(flavor = "multi_thread")]
async fn operation_claim_transfer_receipt_rejects_non_creator_chain() {
    let mut pool = create_and_instantiate_pool(false).await;
    let owner = authenticated_account(&pool);
    let token_0 = pool.runtime.borrow_mut().application_parameters().token_0;
    let token = MemeToken::Fungible(token_0);
    let amount = Amount::from_tokens(5);
    let user_chain_id =
        ChainId::from_str("bee928d4bf3880353b4a3cd9b6f88e6cc6e5ed050860abae439e7782e9b2dfe8")
            .unwrap();

    pool.runtime
        .borrow_mut()
        .set_authenticated_caller_id(token_0);
    pool.state
        .borrow_mut()
        .credit(token, owner, amount)
        .await
        .unwrap();
    pool.state
        .borrow_mut()
        .claim(token, owner, amount)
        .await
        .unwrap();
    pool.runtime.borrow_mut().set_chain_id(user_chain_id);

    let result =
        std::panic::AssertUnwindSafe(pool.execute_operation(PoolOperation::ClaimTransferReceipt {
            receipt: ClaimTransferReceipt {
                owner,
                token: token_0,
                amount,
                result: Ok(()),
            },
        }))
        .catch_unwind()
        .await;

    assert!(result.is_err());
    assert_eq!(
        pool.state
            .borrow()
            .claimable_balance(token, owner)
            .await
            .unwrap(),
        Amount::ZERO
    );
    assert_eq!(
        pool.state
            .borrow()
            .claiming_balance(token, owner)
            .await
            .unwrap(),
        amount
    );
}

#[tokio::test(flavor = "multi_thread")]
async fn operation_claim_transfer_receipt_fail_returns_to_claimable() {
    let mut pool = create_and_instantiate_pool(false).await;
    let owner = authenticated_account(&pool);
    let token_0 = pool.runtime.borrow_mut().application_parameters().token_0;
    let token = MemeToken::Fungible(token_0);
    let amount = Amount::from_tokens(5);

    pool.runtime
        .borrow_mut()
        .set_authenticated_caller_id(token_0);

    pool.state
        .borrow_mut()
        .credit(token, owner, amount)
        .await
        .unwrap();
    pool.state
        .borrow_mut()
        .claim(token, owner, amount)
        .await
        .unwrap();

    pool.execute_operation(PoolOperation::ClaimTransferReceipt {
        receipt: ClaimTransferReceipt {
            owner,
            token: token_0,
            amount,
            result: Err("transfer failed".to_string()),
        },
    })
    .await;

    assert_eq!(
        pool.state
            .borrow()
            .claimable_balance(token, owner)
            .await
            .unwrap(),
        amount
    );
    assert_eq!(
        pool.state
            .borrow()
            .claiming_balance(token, owner)
            .await
            .unwrap(),
        Amount::ZERO
    );
}

#[tokio::test(flavor = "multi_thread")]
async fn operation_claim_transfer_receipt_rejects_insufficient_claiming() {
    let mut pool = create_and_instantiate_pool(false).await;
    let owner = authenticated_account(&pool);
    let token_0 = pool.runtime.borrow_mut().application_parameters().token_0;
    let token = MemeToken::Fungible(token_0);
    let amount = Amount::from_tokens(5);

    pool.runtime
        .borrow_mut()
        .set_authenticated_caller_id(token_0);

    let result =
        std::panic::AssertUnwindSafe(pool.execute_operation(PoolOperation::ClaimTransferReceipt {
            receipt: ClaimTransferReceipt {
                owner,
                token: token_0,
                amount,
                result: Ok(()),
            },
        }))
        .catch_unwind()
        .await;

    assert!(result.is_err());
    assert_eq!(
        pool.state
            .borrow()
            .claiming_balance(token, owner)
            .await
            .unwrap(),
        Amount::ZERO
    );
}

#[tokio::test(flavor = "multi_thread")]
async fn operation_claim_transfer_receipt_rejects_invalid_token() {
    let mut pool = create_and_instantiate_native_pool(false).await;
    let owner = authenticated_account(&pool);
    let invalid_token =
        ApplicationId::from_str("b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bff")
            .unwrap();
    let amount = Amount::from_tokens(5);

    pool.runtime
        .borrow_mut()
        .set_authenticated_caller_id(invalid_token);

    let result =
        std::panic::AssertUnwindSafe(pool.execute_operation(PoolOperation::ClaimTransferReceipt {
            receipt: ClaimTransferReceipt {
                owner,
                token: invalid_token,
                amount,
                result: Ok(()),
            },
        }))
        .catch_unwind()
        .await;

    assert!(result.is_err());
}

#[tokio::test(flavor = "multi_thread")]
async fn message_fund_result_ext_success_funds_pool_chain_with_receipt() {
    let mut pool = create_and_instantiate_pool(false).await;
    let token_0 = pool.runtime.borrow_mut().application_parameters().token_0;
    let token_1 = pool
        .runtime
        .borrow_mut()
        .application_parameters()
        .token_1
        .unwrap();
    let token_chain = mock_token_creator_chain_id();
    let owner_chain = pool.runtime.borrow_mut().chain_id();
    let owner = Account {
        chain_id: owner_chain,
        owner: pool.runtime.borrow_mut().authenticated_signer().unwrap(),
    };
    let request = add_liquidity_fund_request(
        owner,
        Some(token_0),
        Amount::ONE,
        Some(token_1),
        Some(Amount::from_tokens(10)),
    );
    let next = add_liquidity_fund_request(
        owner,
        Some(token_1),
        Amount::from_tokens(10),
        Some(token_0),
        Some(Amount::ONE),
    );

    configure_fund_result_ext_source(&mut pool, token_chain, token_0, owner);

    let captured = Rc::new(RefCell::new(None));
    let captured_for_handler = captured.clone();
    pool.runtime.borrow_mut().set_call_application_handler(
        move |_authenticated, application_id, operation| match bcs::from_bytes::<MemeOperation>(
            &operation,
        ) {
            Ok(MemeOperation::CreatorChainId) => {
                bcs::to_bytes(&MemeResponse::ChainId(mock_token_creator_chain_id())).unwrap()
            }
            _ => {
                *captured_for_handler.borrow_mut() = Some((application_id, operation));
                bcs::to_bytes(&MemeResponse::Ok).unwrap()
            }
        },
    );

    pool.execute_message(PoolMessage::FundResultExt {
        prev: None,
        request: request.clone(),
        next: Some(next.clone()),
        result: Ok(()),
    })
    .await;

    let (application_id, operation) = captured.borrow().clone().unwrap();
    assert_eq!(application_id, token_0);

    let pool_chain_id = pool.runtime.borrow_mut().application_creator_chain_id();
    let pool_application_id = pool.runtime.borrow_mut().application_id().forget_abi();
    let pool_account = Account {
        chain_id: pool_chain_id,
        owner: AccountOwner::from(pool_application_id),
    };

    assert!(matches!(
        bcs::from_bytes::<MemeOperation>(&operation).unwrap(),
        MemeOperation::TransferFromApplicationWithReceipt {
            to,
            amount,
            receipt,
        } if to == pool_account
            && amount == request.amount_in
            && receipt.purpose == TransferFromApplicationReceiptPurpose::PoolAddLiquidity
            && receipt.owner == owner
            && receipt.token == token_0
            && receipt.amount == request.amount_in
            && receipt.result.is_none()
            && matches!(
                &receipt.payload,
                Some(TransferFromApplicationReceiptPayload::PoolAddLiquidity(payload))
                    if payload.prev.is_none()
                        && payload.request.amount_in == request.amount_in
                        && payload.next.as_ref().map(|value| value.amount_in) == Some(next.amount_in)
            )
    ));

    assert!(!pool
        .runtime
        .borrow()
        .created_send_message_requests()
        .iter()
        .any(|request| matches!(request.message, PoolMessage::AddLiquidity { .. })));
}

#[tokio::test(flavor = "multi_thread")]
async fn message_fund_result_ext_fail_credits_prev_without_funding_pool_chain() {
    let mut pool = create_and_instantiate_pool(false).await;
    let token_0 = pool.runtime.borrow_mut().application_parameters().token_0;
    let token_1 = pool
        .runtime
        .borrow_mut()
        .application_parameters()
        .token_1
        .unwrap();
    let token_chain = mock_token_creator_chain_id();
    let owner_chain = pool.runtime.borrow_mut().chain_id();
    let owner = Account {
        chain_id: owner_chain,
        owner: pool.runtime.borrow_mut().authenticated_signer().unwrap(),
    };
    let prev = add_liquidity_fund_request(
        owner,
        Some(token_0),
        Amount::ONE,
        Some(token_1),
        Some(Amount::from_tokens(10)),
    );
    let request = add_liquidity_fund_request(
        owner,
        Some(token_1),
        Amount::from_tokens(10),
        Some(token_0),
        Some(Amount::ONE),
    );

    configure_fund_result_ext_source(&mut pool, token_chain, token_1, owner);

    let captured = Rc::new(RefCell::new(None));
    let captured_for_handler = captured.clone();
    pool.runtime.borrow_mut().set_call_application_handler(
        move |_authenticated, application_id, operation| match bcs::from_bytes::<MemeOperation>(
            &operation,
        ) {
            Ok(MemeOperation::CreatorChainId) => {
                bcs::to_bytes(&MemeResponse::ChainId(mock_token_creator_chain_id())).unwrap()
            }
            _ => {
                *captured_for_handler.borrow_mut() = Some((application_id, operation));
                bcs::to_bytes(&MemeResponse::Ok).unwrap()
            }
        },
    );

    pool.execute_message(PoolMessage::FundResultExt {
        prev: Some(prev.clone()),
        request,
        next: None,
        result: Err("fund failed".to_string()),
    })
    .await;

    assert!(captured.borrow().is_none());
    assert_eq!(
        pool.state
            .borrow()
            .claimable_balance(MemeToken::Fungible(token_0), owner)
            .await
            .unwrap(),
        prev.amount_in
    );
}

#[tokio::test(flavor = "multi_thread")]
async fn operation_add_liquidity_transfer_receipt_success_continues_next_fungible_leg() {
    let mut pool = create_and_instantiate_pool(false).await;
    let token_0 = pool.runtime.borrow_mut().application_parameters().token_0;
    let token_1 = pool
        .runtime
        .borrow_mut()
        .application_parameters()
        .token_1
        .unwrap();
    let owner = authenticated_account(&pool);
    let request = add_liquidity_fund_request(
        owner,
        Some(token_0),
        Amount::ONE,
        Some(token_1),
        Some(Amount::from_tokens(10)),
    );
    let next = add_liquidity_fund_request(
        owner,
        Some(token_1),
        Amount::from_tokens(10),
        Some(token_0),
        Some(Amount::ONE),
    );

    pool.runtime
        .borrow_mut()
        .set_authenticated_caller_id(token_0);

    pool.execute_operation(PoolOperation::AddLiquidityTransferReceipt {
        receipt: AddLiquidityTransferReceipt {
            result: Ok(()),
            prev: None,
            request: request.clone(),
            next: Some(next.clone()),
        },
    })
    .await;

    let runtime = pool.runtime.borrow();
    let requests = runtime.created_send_message_requests();
    let request_message = requests
        .iter()
        .find(|request| matches!(request.message, PoolMessage::RequestFundExt { .. }))
        .unwrap();
    assert!(request_message.authenticated);
    assert!(!request_message.is_tracked);
    assert!(matches!(
        &request_message.message,
        PoolMessage::RequestFundExt {
            prev,
            request: current,
            next: following,
        } if prev.as_ref().map(|value| value.amount_in) == Some(request.amount_in)
            && current.amount_in == next.amount_in
            && following.is_none()
    ));
}

#[tokio::test(flavor = "multi_thread")]
async fn operation_add_liquidity_transfer_receipt_success_forwards_last_leg_to_pool_creator_chain()
{
    let mut pool = create_and_instantiate_pool(false).await;
    let token_0 = pool.runtime.borrow_mut().application_parameters().token_0;
    let token_1 = pool
        .runtime
        .borrow_mut()
        .application_parameters()
        .token_1
        .unwrap();
    let owner = authenticated_account(&pool);
    let prev = add_liquidity_fund_request(
        owner,
        Some(token_0),
        Amount::ONE,
        Some(token_1),
        Some(Amount::from_tokens(10)),
    );
    let request = add_liquidity_fund_request(
        owner,
        Some(token_1),
        Amount::from_tokens(10),
        Some(token_0),
        Some(Amount::ONE),
    );

    pool.runtime
        .borrow_mut()
        .set_authenticated_caller_id(token_1);

    pool.execute_operation(PoolOperation::AddLiquidityTransferReceipt {
        receipt: AddLiquidityTransferReceipt {
            result: Ok(()),
            prev: Some(prev),
            request: request.clone(),
            next: None,
        },
    })
    .await;

    let destination = pool.runtime.borrow_mut().application_creator_chain_id();
    let runtime = pool.runtime.borrow();
    let requests = runtime.created_send_message_requests();
    let request_message = requests
        .iter()
        .find(|request| {
            matches!(
                request.message,
                PoolMessage::AddLiquidityTransferReceipt { .. }
            )
        })
        .unwrap();
    assert_eq!(request_message.destination, destination);
    assert!(request_message.authenticated);
    assert!(!request_message.is_tracked);
    assert!(matches!(
        &request_message.message,
        PoolMessage::AddLiquidityTransferReceipt { receipt }
            if receipt.result.is_ok()
                && receipt.request.amount_in == request.amount_in
                && receipt.next.is_none()
    ));
}

#[tokio::test(flavor = "multi_thread")]
async fn operation_add_liquidity_transfer_receipt_success_funds_native_next_leg() {
    let mut pool = create_and_instantiate_native_pool(false).await;
    let token_0 = pool.runtime.borrow_mut().application_parameters().token_0;
    let owner = authenticated_account(&pool);
    let request = add_liquidity_fund_request(
        owner,
        Some(token_0),
        Amount::ONE,
        None,
        Some(Amount::from_tokens(10)),
    );
    let next = add_liquidity_fund_request(
        owner,
        None,
        Amount::from_tokens(10),
        Some(token_0),
        Some(Amount::ONE),
    );
    let application_owner = AccountOwner::from(pool.runtime.borrow_mut().application_id());

    pool.runtime
        .borrow_mut()
        .set_authenticated_caller_id(token_0);
    pool.runtime
        .borrow_mut()
        .set_chain_balance(Amount::from_tokens(10));
    pool.runtime
        .borrow_mut()
        .set_owner_balance(owner.owner, Amount::from_tokens(10));
    pool.runtime
        .borrow_mut()
        .set_owner_balance(application_owner, Amount::ZERO);

    pool.execute_operation(PoolOperation::AddLiquidityTransferReceipt {
        receipt: AddLiquidityTransferReceipt {
            result: Ok(()),
            prev: None,
            request,
            next: Some(next),
        },
    })
    .await;

    assert_eq!(
        pool.runtime.borrow_mut().owner_balance(application_owner),
        Amount::from_tokens(10)
    );
}

#[tokio::test(flavor = "multi_thread")]
async fn message_add_liquidity_transfer_receipt_success_finalizes_after_last_leg() {
    let mut pool = create_and_instantiate_pool(false).await;
    let token_0 = pool.runtime.borrow_mut().application_parameters().token_0;
    let token_1 = pool
        .runtime
        .borrow_mut()
        .application_parameters()
        .token_1
        .unwrap();
    let owner = authenticated_account(&pool);
    let prev = add_liquidity_fund_request(
        owner,
        Some(token_0),
        Amount::ONE,
        Some(token_1),
        Some(Amount::from_tokens(10)),
    );
    let request = add_liquidity_fund_request(
        owner,
        Some(token_1),
        Amount::from_tokens(10),
        Some(token_0),
        Some(Amount::ONE),
    );

    pool.execute_message(PoolMessage::AddLiquidityTransferReceipt {
        receipt: AddLiquidityTransferReceipt {
            result: Ok(()),
            prev: Some(prev),
            request,
            next: None,
        },
    })
    .await;

    let destination = pool.runtime.borrow_mut().application_creator_chain_id();
    let runtime = pool.runtime.borrow();
    let requests = runtime.created_send_message_requests();
    let request_message = requests.last().unwrap();
    assert_eq!(request_message.destination, destination);
    assert!(request_message.authenticated);
    assert!(!request_message.is_tracked);
    assert!(matches!(
        request_message.message,
        PoolMessage::AddLiquidity {
            origin,
            amount_0_in,
            amount_1_in,
            ..
        } if origin == owner
            && amount_0_in == Amount::ONE
            && amount_1_in == Amount::from_tokens(10)
    ));
}

#[tokio::test(flavor = "multi_thread")]
async fn message_add_liquidity_transfer_receipt_fail_credits_only_prev() {
    let mut pool = create_and_instantiate_pool(false).await;
    let token_0 = pool.runtime.borrow_mut().application_parameters().token_0;
    let token_1 = pool
        .runtime
        .borrow_mut()
        .application_parameters()
        .token_1
        .unwrap();
    let owner = authenticated_account(&pool);
    let prev = add_liquidity_fund_request(
        owner,
        Some(token_0),
        Amount::ONE,
        Some(token_1),
        Some(Amount::from_tokens(10)),
    );
    let request = add_liquidity_fund_request(
        owner,
        Some(token_1),
        Amount::from_tokens(10),
        Some(token_0),
        Some(Amount::ONE),
    );

    pool.execute_message(PoolMessage::AddLiquidityTransferReceipt {
        receipt: AddLiquidityTransferReceipt {
            result: Err("transfer failed".to_string()),
            prev: Some(prev.clone()),
            request: request.clone(),
            next: None,
        },
    })
    .await;

    assert_eq!(
        pool.state
            .borrow()
            .claimable_balance(MemeToken::Fungible(token_0), owner)
            .await
            .unwrap(),
        prev.amount_in
    );
    assert_eq!(
        pool.state
            .borrow()
            .claimable_balance(MemeToken::Fungible(token_1), owner)
            .await
            .unwrap(),
        Amount::ZERO
    );
}

#[tokio::test(flavor = "multi_thread")]
async fn operation_add_liquidity_transfer_receipt_rejects_wrong_caller_app() {
    let mut pool = create_and_instantiate_pool(false).await;
    let token_0 = pool.runtime.borrow_mut().application_parameters().token_0;
    let token_1 = pool
        .runtime
        .borrow_mut()
        .application_parameters()
        .token_1
        .unwrap();
    let owner = authenticated_account(&pool);
    let request = add_liquidity_fund_request(
        owner,
        Some(token_0),
        Amount::ONE,
        Some(token_1),
        Some(Amount::from_tokens(10)),
    );

    pool.runtime
        .borrow_mut()
        .set_authenticated_caller_id(token_1);

    let result = std::panic::AssertUnwindSafe(pool.execute_operation(
        PoolOperation::AddLiquidityTransferReceipt {
            receipt: AddLiquidityTransferReceipt {
                result: Ok(()),
                prev: None,
                request,
                next: None,
            },
        },
    ))
    .catch_unwind()
    .await;

    assert!(result.is_err());
    assert!(pool
        .runtime
        .borrow()
        .created_send_message_requests()
        .iter()
        .all(|request| !matches!(request.message, PoolMessage::AddLiquidity { .. })));
}

#[tokio::test(flavor = "multi_thread")]
async fn message_add_liquidity_transfer_receipt_rejects_wrong_chain_without_credit() {
    let mut pool = create_and_instantiate_pool(false).await;
    let token_0 = pool.runtime.borrow_mut().application_parameters().token_0;
    let token_1 = pool
        .runtime
        .borrow_mut()
        .application_parameters()
        .token_1
        .unwrap();
    let owner = authenticated_account(&pool);
    let user_chain_id =
        ChainId::from_str("bee928d4bf3880353b4a3cd9b6f88e6cc6e5ed050860abae439e7782e9b2dfe8")
            .unwrap();
    let prev = add_liquidity_fund_request(
        owner,
        Some(token_0),
        Amount::ONE,
        Some(token_1),
        Some(Amount::from_tokens(10)),
    );
    let request = add_liquidity_fund_request(
        owner,
        Some(token_1),
        Amount::from_tokens(10),
        Some(token_0),
        Some(Amount::ONE),
    );

    pool.runtime.borrow_mut().set_chain_id(user_chain_id);

    let result = std::panic::AssertUnwindSafe(pool.execute_message(
        PoolMessage::AddLiquidityTransferReceipt {
            receipt: AddLiquidityTransferReceipt {
                result: Err("transfer failed".to_string()),
                prev: Some(prev),
                request,
                next: None,
            },
        },
    ))
    .catch_unwind()
    .await;

    assert!(result.is_err());
    assert_eq!(
        pool.state
            .borrow()
            .claimable_balance(MemeToken::Fungible(token_0), owner)
            .await
            .unwrap(),
        Amount::ZERO
    );
}

#[tokio::test(flavor = "multi_thread")]
async fn message_fund_result_ext_swap_fail_does_not_credit_or_update_reserves() {
    let mut pool = create_and_initialize_pool(false).await;
    let token_0 = pool.runtime.borrow_mut().application_parameters().token_0;
    let token_chain = mock_token_creator_chain_id();
    let owner = authenticated_account(&pool);
    let request =
        FundRequestExt::builder(owner, Some(token_0), Amount::ONE, FundRequestExtType::Swap)
            .counterparty_token(pool.runtime.borrow_mut().application_parameters().token_1)
            .counterparty_amount_out_min(Some(Amount::from_attos(1)))
            .build();
    let reserve_0 = pool.state.borrow().reserve_0();
    let reserve_1 = pool.state.borrow().reserve_1();
    let message_count_before = pool.runtime.borrow().created_send_message_requests().len();

    configure_fund_result_ext_source(&mut pool, token_chain, token_0, owner);
    pool.execute_message(PoolMessage::FundResultExt {
        prev: None,
        request: request.clone(),
        next: None,
        result: Err("fund failed".to_string()),
    })
    .await;

    assert_eq!(pool.state.borrow().reserve_0(), reserve_0);
    assert_eq!(pool.state.borrow().reserve_1(), reserve_1);
    assert_eq!(
        pool.state
            .borrow()
            .claimable_balance(MemeToken::Fungible(token_0), owner)
            .await
            .unwrap(),
        Amount::ZERO
    );
    assert_eq!(
        pool.runtime.borrow().created_send_message_requests().len(),
        message_count_before
    );
}

#[tokio::test(flavor = "multi_thread")]
async fn message_fund_result_ext_swap_success_requests_pool_chain_custody_with_receipt() {
    let mut pool = create_and_initialize_pool(false).await;
    let token_0 = pool.runtime.borrow_mut().application_parameters().token_0;
    let token_chain = mock_token_creator_chain_id();
    let owner = authenticated_account(&pool);
    let request =
        FundRequestExt::builder(owner, Some(token_0), Amount::ONE, FundRequestExtType::Swap)
            .counterparty_token(pool.runtime.borrow_mut().application_parameters().token_1)
            .counterparty_amount_out_min(Some(Amount::from_attos(1)))
            .build();

    configure_fund_result_ext_source(&mut pool, token_chain, token_0, owner);

    let captured = Rc::new(RefCell::new(None));
    let captured_for_handler = captured.clone();
    pool.runtime.borrow_mut().set_call_application_handler(
        move |_authenticated, application_id, operation| match bcs::from_bytes::<MemeOperation>(
            &operation,
        ) {
            Ok(MemeOperation::CreatorChainId) => {
                bcs::to_bytes(&MemeResponse::ChainId(mock_token_creator_chain_id())).unwrap()
            }
            _ => {
                *captured_for_handler.borrow_mut() = Some((application_id, operation));
                bcs::to_bytes(&MemeResponse::Ok).unwrap()
            }
        },
    );

    pool.execute_message(PoolMessage::FundResultExt {
        prev: None,
        request: request.clone(),
        next: None,
        result: Ok(()),
    })
    .await;

    let (application_id, operation) = captured.borrow().clone().unwrap();
    assert_eq!(application_id, token_0);

    let pool_chain_id = pool.runtime.borrow_mut().application_creator_chain_id();
    let pool_application_id = pool.runtime.borrow_mut().application_id().forget_abi();
    let pool_account = Account {
        chain_id: pool_chain_id,
        owner: AccountOwner::from(pool_application_id),
    };

    assert!(matches!(
        bcs::from_bytes::<MemeOperation>(&operation).unwrap(),
        MemeOperation::TransferFromApplicationWithReceipt {
            to,
            amount,
            receipt,
        } if to == pool_account
            && amount == request.amount_in
            && receipt.purpose == TransferFromApplicationReceiptPurpose::PoolSwap
            && receipt.owner == owner
            && receipt.token == token_0
            && receipt.amount == request.amount_in
            && receipt.result.is_none()
            && matches!(
                &receipt.payload,
                Some(TransferFromApplicationReceiptPayload::PoolSwap(payload))
                    if payload.request.amount_in == request.amount_in
                        && payload.request.fund_type == FundRequestExtType::Swap
            )
    ));
}

#[tokio::test(flavor = "multi_thread")]
async fn operation_swap_transfer_receipt_forwards_to_pool_creator_chain() {
    let mut pool = create_and_initialize_pool(false).await;
    let token_0 = pool.runtime.borrow_mut().application_parameters().token_0;
    let owner = authenticated_account(&pool);
    let request =
        FundRequestExt::builder(owner, Some(token_0), Amount::ONE, FundRequestExtType::Swap)
            .counterparty_token(pool.runtime.borrow_mut().application_parameters().token_1)
            .counterparty_amount_out_min(Some(Amount::from_attos(1)))
            .build();
    let destination = pool.runtime.borrow_mut().application_creator_chain_id();
    let message_count_before = pool.runtime.borrow().created_send_message_requests().len();

    pool.runtime
        .borrow_mut()
        .set_authenticated_caller_id(token_0);

    pool.execute_operation(PoolOperation::SwapTransferReceipt {
        receipt: SwapTransferReceipt {
            result: Ok(()),
            request: request.clone(),
        },
    })
    .await;

    let runtime = pool.runtime.borrow();
    let messages = &runtime.created_send_message_requests()[message_count_before..];
    assert_eq!(messages.len(), 1);
    assert_eq!(messages[0].destination, destination);
    assert!(messages[0].authenticated);
    assert!(!messages[0].is_tracked);
    assert!(matches!(
        &messages[0].message,
        PoolMessage::SwapTransferReceipt { receipt }
            if receipt.result.is_ok()
                && receipt.request.amount_in == request.amount_in
                && receipt.request.fund_type == FundRequestExtType::Swap
    ));
}

#[tokio::test(flavor = "multi_thread")]
async fn message_swap_transfer_receipt_success_queues_final_swap_on_pool_creator_chain() {
    let mut pool = create_and_initialize_pool(false).await;
    let token_0 = pool.runtime.borrow_mut().application_parameters().token_0;
    let owner = authenticated_account(&pool);
    let request =
        FundRequestExt::builder(owner, Some(token_0), Amount::ONE, FundRequestExtType::Swap)
            .counterparty_token(pool.runtime.borrow_mut().application_parameters().token_1)
            .counterparty_amount_out_min(Some(Amount::from_attos(1)))
            .build();
    let pool_application_id = pool.runtime.borrow_mut().application_id().forget_abi();

    pool.runtime
        .borrow_mut()
        .set_message_origin_chain_id(owner.chain_id);
    pool.runtime
        .borrow_mut()
        .set_authenticated_caller_id(pool_application_id);
    let message_count_before = pool.runtime.borrow().created_send_message_requests().len();

    pool.execute_message(PoolMessage::SwapTransferReceipt {
        receipt: SwapTransferReceipt {
            result: Ok(()),
            request: request.clone(),
        },
    })
    .await;

    let runtime = pool.runtime.borrow();
    let messages = &runtime.created_send_message_requests()[message_count_before..];
    assert_eq!(messages.len(), 1);
    assert!(messages[0].authenticated);
    assert!(!messages[0].is_tracked);
    assert!(matches!(
        &messages[0].message,
        PoolMessage::Swap {
            origin,
            amount_0_in: Some(amount_0_in),
            amount_1_in: None,
            amount_1_out_min,
            ..
        } if *origin == owner
            && *amount_0_in == Amount::ONE
            && *amount_1_out_min == Some(Amount::from_attos(1))
    ));
}

#[tokio::test(flavor = "multi_thread")]
async fn message_swap_transfer_receipt_fail_does_not_queue_final_swap() {
    let mut pool = create_and_initialize_pool(false).await;
    let token_0 = pool.runtime.borrow_mut().application_parameters().token_0;
    let owner = authenticated_account(&pool);
    let request =
        FundRequestExt::builder(owner, Some(token_0), Amount::ONE, FundRequestExtType::Swap)
            .counterparty_token(pool.runtime.borrow_mut().application_parameters().token_1)
            .counterparty_amount_out_min(Some(Amount::from_attos(1)))
            .build();
    let pool_application_id = pool.runtime.borrow_mut().application_id().forget_abi();

    pool.runtime
        .borrow_mut()
        .set_message_origin_chain_id(owner.chain_id);
    pool.runtime
        .borrow_mut()
        .set_authenticated_caller_id(pool_application_id);
    let message_count_before = pool.runtime.borrow().created_send_message_requests().len();

    pool.execute_message(PoolMessage::SwapTransferReceipt {
        receipt: SwapTransferReceipt {
            result: Err("transfer failed".to_string()),
            request,
        },
    })
    .await;

    assert_eq!(
        pool.runtime.borrow().created_send_message_requests().len(),
        message_count_before
    );
}

#[tokio::test(flavor = "multi_thread")]
async fn message_swap_slippage_after_custody_credits_input_claim_without_reserve_update() {
    let mut pool = create_and_initialize_pool(false).await;
    let owner = authenticated_account(&pool);
    let reserve_0 = pool.state.borrow().reserve_0();
    let reserve_1 = pool.state.borrow().reserve_1();
    let amount_1_in = Amount::ONE;
    let exact_amount_0_out = pool
        .state
        .borrow()
        .calculate_swap_amount_0(amount_1_in)
        .unwrap();
    let message_count_before = pool.runtime.borrow().created_send_message_requests().len();

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
            .claimable_balance(
                MemeToken::from(pool.runtime.borrow_mut().application_parameters().token_1),
                owner
            )
            .await
            .unwrap(),
        amount_1_in
    );
    let runtime = pool.runtime.borrow();
    assert!(
        runtime.created_send_message_requests()[message_count_before..]
            .iter()
            .all(|message| !matches!(message.message, PoolMessage::NewTransaction { .. }))
    );
}

#[tokio::test(flavor = "multi_thread")]
async fn message_fund_result_ext_rejects_forged_signer_without_calling_token_app() {
    let mut pool = create_and_instantiate_pool(false).await;
    let token_0 = pool.runtime.borrow_mut().application_parameters().token_0;
    let token_1 = pool
        .runtime
        .borrow_mut()
        .application_parameters()
        .token_1
        .unwrap();
    let token_chain = mock_token_creator_chain_id();
    let owner = Account {
        chain_id: token_chain,
        owner: pool.runtime.borrow_mut().authenticated_signer().unwrap(),
    };
    let request = add_liquidity_fund_request(
        owner,
        Some(token_0),
        Amount::ONE,
        Some(token_1),
        Some(Amount::from_tokens(10)),
    );

    configure_fund_result_ext_source(&mut pool, token_chain, token_0, owner);
    pool.runtime
        .borrow_mut()
        .set_authenticated_signer(Some(alternate_account(token_chain).owner));

    let captured = Rc::new(RefCell::new(None));
    let captured_for_handler = captured.clone();
    pool.runtime.borrow_mut().set_call_application_handler(
        move |_authenticated, application_id, operation| match bcs::from_bytes::<MemeOperation>(
            &operation,
        ) {
            Ok(MemeOperation::CreatorChainId) => {
                bcs::to_bytes(&MemeResponse::ChainId(mock_token_creator_chain_id())).unwrap()
            }
            _ => {
                *captured_for_handler.borrow_mut() = Some((application_id, operation));
                bcs::to_bytes(&MemeResponse::Ok).unwrap()
            }
        },
    );

    let result = std::panic::AssertUnwindSafe(pool.execute_message(PoolMessage::FundResultExt {
        prev: None,
        request,
        next: None,
        result: Ok(()),
    }))
    .catch_unwind()
    .await;

    assert!(result.is_err());
    assert!(captured.borrow().is_none());
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

fn alternate_account(chain_id: ChainId) -> Account {
    Account {
        chain_id,
        owner: AccountOwner::from_str(
            "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        )
        .unwrap(),
    }
}

fn mock_token_creator_chain_id() -> ChainId {
    ChainId::from_str("aee928d4bf3880353b4a3cd9b6f88e6cc6e5ed050860abae439e7782e9b2dfe9").unwrap()
}

fn add_liquidity_fund_request(
    from: Account,
    token: Option<ApplicationId>,
    amount_in: Amount,
    counterparty_token: Option<ApplicationId>,
    counterparty_amount_in: Option<Amount>,
) -> FundRequestExt {
    FundRequestExt {
        from,
        token,
        amount_in,
        amount_out_min: None,
        counterparty_token,
        counterparty_amount_in,
        counterparty_amount_out_min: None,
        to: None,
        block_timestamp: None,
        fund_type: FundRequestExtType::AddLiquidity,
    }
}

fn configure_fund_result_ext_source(
    pool: &mut PoolContract,
    token_chain: ChainId,
    _token: ApplicationId,
    signer: Account,
) {
    let pool_application_id = pool.runtime.borrow_mut().application_id().forget_abi();
    pool.runtime
        .borrow_mut()
        .set_message_origin_chain_id(token_chain);
    pool.runtime
        .borrow_mut()
        .set_authenticated_caller_id(pool_application_id);
    pool.runtime
        .borrow_mut()
        .set_authenticated_signer(Some(signer.owner));

    assert_eq!(
        pool.runtime.borrow_mut().message_origin_chain_id(),
        Some(token_chain)
    );
    assert_eq!(
        pool.runtime.borrow_mut().authenticated_signer(),
        Some(signer.owner)
    );
    assert_eq!(
        pool.runtime.borrow_mut().authenticated_caller_id(),
        Some(pool_application_id)
    );
}

fn total_supply(pool: &PoolContract) -> Amount {
    *pool.state.borrow().total_supply.get()
}

async fn create_and_instantiate_pool(virtual_initial_liquidity: bool) -> PoolContract {
    create_and_instantiate_pool_with_amounts(virtual_initial_liquidity).await
}

async fn create_and_instantiate_native_pool(virtual_initial_liquidity: bool) -> PoolContract {
    let pool = create_and_instantiate_pool_with_amounts(virtual_initial_liquidity).await;
    let mut parameters = pool.runtime.borrow_mut().application_parameters();
    parameters.token_1 = None;
    pool.runtime
        .borrow_mut()
        .set_application_parameters(parameters);

    let mut state_pool = pool.state.borrow().pool();
    state_pool.token_1 = None;
    pool.state.borrow_mut().pool.set(Some(state_pool));

    pool
}

async fn create_and_instantiate_user_pool() -> PoolContract {
    let pool = create_and_instantiate_pool_with_amounts(false).await;
    let mut parameters = pool.runtime.borrow_mut().application_parameters();
    parameters.bootstrap_policy = BootstrapPolicy::UserCreatePool;
    pool.runtime
        .borrow_mut()
        .set_application_parameters(parameters);
    pool
}

async fn create_and_initialize_pool(virtual_initial_liquidity: bool) -> PoolContract {
    let mut pool = create_and_instantiate_pool(virtual_initial_liquidity).await;
    let origin = authenticated_account(&pool);

    pool.execute_message(PoolMessage::InitializeLiquidity {
        origin,
        amount_0_in: Amount::from_str("1000").unwrap(),
        amount_1_in: Amount::from_str("10").unwrap(),
        to: None,
        block_timestamp: None,
    })
    .await;

    pool
}

async fn create_and_instantiate_pool_with_amounts(virtual_initial_liquidity: bool) -> PoolContract {
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
            bootstrap_policy: BootstrapPolicy::MemeInitializeLiquidity {
                virtual_initial_liquidity,
            },
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
            pool_fee_percent_mul_100: 30,
            router_application_id,
        })
        .await;

    contract
}
