use super::{MemeContract, MemeState as BusinessState};

use abi::{
    meme::{
        state_v1::{
            InitializeArgument, MemeStateV1Operation, MemeStateV1Response,
            StateInstantiationArgument,
        },
        InstantiationArgument, Liquidity, Meme, MemeAbi, MemeMessage, MemeOperation,
        MemeParameters, MemeResponse, Metadata, TransferFromApplicationReceipt,
        TransferFromApplicationReceiptPayload, TransferFromApplicationReceiptPurpose,
    },
    store_type::StoreType,
    swap::pool::{
        AddLiquidityTransferReceiptPayload, ClaimTransferReceipt, FundRequest, FundType,
        PoolInitializeLiquidityCall, PoolOperation, PoolResponse, SwapTransferReceiptPayload,
    },
};
use futures::FutureExt as _;
use linera_sdk::{
    bcs,
    linera_base_types::{
        Account, AccountOwner, Amount, ApplicationId, BlockHeight, ChainId, ChainOwnership,
        CryptoHash, TestString, Timestamp,
    },
    util::BlockingWait,
    views::View,
    Contract, ContractRuntime,
};
use meme_state::{interfaces::state::StateInterface, state::MemeState as StateAppState};
use runtime::{
    contract::ContractRuntimeAdapter,
    interfaces::{base::BaseRuntimeContext, contract::ContractRuntimeContext},
};
use std::{cell::RefCell, rc::Rc};
use std::str::FromStr;

#[tokio::test(flavor = "multi_thread")]
async fn message_transfer() {
    let (mut meme, state) = create_and_instantiate_meme(false, None).await;
    let mut runtime_context = ContractRuntimeAdapter::new(meme.runtime.clone());

    let from = runtime_context.authenticated_account();
    let amount = initial_owner_balance(&meme);

    let to = Account {
        chain_id: runtime_context.chain_id(),
        owner: AccountOwner::from_str(
            "0x5279b3ae14d3b38e14b65a74aefe44824ea88b25c7841836e9ec77d991a5bc8f",
        )
        .unwrap(),
    };

    assert_eq!(balance_of(&state, from).await, amount);

    meme.execute_message(MemeMessage::Transfer { from, to, amount })
        .await;

    assert_eq!(balance_of(&state, from).await, Amount::ZERO);
    assert_eq!(balance_of(&state, to).await, amount);
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic(expected = "Insufficient funds")]
async fn message_transfer_insufficient_funds() {
    let (mut meme, state) = create_and_instantiate_meme(false, None).await;
    let mut runtime_context = ContractRuntimeAdapter::new(meme.runtime.clone());

    let from = runtime_context.authenticated_account();
    let amount = initial_owner_balance(&meme);
    let transfer_amount = amount.try_add(Amount::ONE).unwrap();

    let to = Account {
        chain_id: runtime_context.chain_id(),
        owner: AccountOwner::from_str(
            "0x5279b3ae14d3b38e14b65a74aefe44824ea88b25c7841836e9ec77d991a5bc8f",
        )
        .unwrap(),
    };

    assert_eq!(balance_of(&state, from).await, amount);

    meme.execute_message(MemeMessage::Transfer {
        from,
        to,
        amount: transfer_amount,
    })
    .await;
}

#[tokio::test(flavor = "multi_thread")]
async fn message_approve_owner_success() {
    let (mut meme, state) = create_and_instantiate_meme(false, None).await;
    let mut runtime_context = ContractRuntimeAdapter::new(meme.runtime.clone());

    let from = runtime_context.authenticated_account();
    let amount = initial_owner_balance(&meme);
    let allowance = Amount::from_tokens(22);

    let spender = Account {
        chain_id: runtime_context.chain_id(),
        owner: AccountOwner::from_str(
            "0x5279b3ae14d3b38e14b65a74aefe44824ea88b25c7841836e9ec77d991a5bc8f",
        )
        .unwrap(),
    };

    assert_eq!(balance_of(&state, from).await, amount);

    meme.execute_message(MemeMessage::Approve {
        owner: from,
        spender,
        amount: allowance,
    })
    .await;

    assert_eq!(balance_of(&state, from).await, amount.try_sub(allowance).unwrap());
    assert_eq!(allowance_of(&state, from, spender).await, allowance);

    meme.execute_message(MemeMessage::Approve {
        owner: from,
        spender,
        amount: allowance,
    })
    .await;

    assert_eq!(
        balance_of(&state, from).await,
        amount.try_sub(allowance).unwrap().try_sub(allowance).unwrap()
    );
    assert_eq!(allowance_of(&state, from, spender).await, allowance.try_mul(2).unwrap());

    let to = Account {
        chain_id: runtime_context.chain_id(),
        owner: AccountOwner::from_str(
            "0x02e900512d2fca22897f80a2f6932ff454f2752ef7afad18729dd25e5b5b6e08",
        )
        .unwrap(),
    };

    meme.execute_message(MemeMessage::TransferFrom {
        owner: spender,
        from,
        to,
        amount: allowance,
    })
    .await;

    assert_eq!(allowance_of(&state, from, spender).await, allowance);
    assert_eq!(balance_of(&state, to).await, allowance);
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic(expected = "Insufficient funds")]
async fn message_approve_insufficient_balance() {
    let (mut meme, state) = create_and_instantiate_meme(false, None).await;
    let mut runtime_context = ContractRuntimeAdapter::new(meme.runtime.clone());

    let from = runtime_context.authenticated_account();
    let amount = initial_owner_balance(&meme);
    let allowance = Amount::from_tokens(220);

    let spender = Account {
        chain_id: runtime_context.chain_id(),
        owner: AccountOwner::from_str(
            "0x5279b3ae14d3b38e14b65a74aefe44824ea88b25c7841836e9ec77d991a5bc8f",
        )
        .unwrap(),
    };

    assert_eq!(balance_of(&state, from).await, amount);

    meme.execute_message(MemeMessage::Approve {
        owner: from,
        spender,
        amount: allowance,
    })
    .await;
}

#[tokio::test(flavor = "multi_thread")]
async fn operation_transfer_from_application_with_receipt_sends_request_message() {
    let (mut meme, _state) = create_and_instantiate_meme(false, None).await;
    let receipt = pool_claim_receipt(None);
    let to = alternate_account(meme.runtime.borrow_mut().chain_id());
    let amount = Amount::from_tokens(5);

    let expected_destination = meme.runtime.borrow_mut().application_creator_chain_id();
    let caller_id = meme.runtime.borrow_mut().authenticated_caller_id().unwrap();
    let expected_caller = Account {
        chain_id: meme.runtime.borrow_mut().chain_id(),
        owner: AccountOwner::from(caller_id),
    };

    let response = meme
        .execute_operation(MemeOperation::TransferFromApplicationWithReceipt {
            to,
            amount,
            receipt: receipt.clone(),
        })
        .await;

    assert!(matches!(response, MemeResponse::Ok));
    let runtime = meme.runtime.borrow();
    let requests = runtime.created_send_message_requests();
    assert_eq!(requests.len(), 2);
    let request = requests.last().unwrap();
    assert_eq!(request.destination, expected_destination);
    assert!(request.authenticated);
    assert!(request.is_tracked);

    assert!(matches!(
        &request.message,
        MemeMessage::TransferFromApplicationWithReceipt {
            caller,
            to: request_to,
            amount: request_amount,
            receipt: request_receipt,
        } if *caller == expected_caller
            && *request_to == to
            && *request_amount == amount
            && request_receipt.purpose == receipt.purpose
            && request_receipt.owner == receipt.owner
            && request_receipt.token == receipt.token
            && request_receipt.amount == receipt.amount
            && request_receipt.result == receipt.result
    ));
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic(expected = "Not enabled")]
async fn operation_mine_not_enable_mining() {
    let (mut meme, _state) = create_and_instantiate_meme(false, None).await;

    let _ = meme
        .execute_operation(MemeOperation::Mine {
            nonce: CryptoHash::new(&TestString::new("aaaa")),
        })
        .now_or_never()
        .expect("Execution of meme operation should not await anything");
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic(expected = "Invalid nonce")]
async fn operation_mine_enable_mining_supply_none_invalid_nonce() {
    let (mut meme, _state) = create_and_instantiate_meme(true, None).await;

    let _ = meme
        .execute_operation(MemeOperation::Mine {
            nonce: CryptoHash::new(&TestString::new("aaaa")),
        })
        .now_or_never()
        .expect("Execution of meme operation should not await anything");
}

#[tokio::test(flavor = "multi_thread")]
async fn operation_mine_enable_mining_supply_none_one_block() {
    let (mut meme, _state) = create_and_instantiate_meme(true, None).await;

    let _ = meme
        .execute_operation(MemeOperation::Mine {
            nonce: CryptoHash::from_str(
                "6e29f698682cedf788f02e2299e6428539dd40b8f262152473d4a6e6e6ee78a1",
            )
            .unwrap(),
        })
        .now_or_never()
        .expect("Execution of meme operation should not await anything");

    // TODO: check reward balance
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic(expected = "Stale block height")]
async fn operation_mine_enable_mining_supply_none_two_block() {
    let (mut meme, _state) = create_and_instantiate_meme(true, None).await;

    let _ = meme
        .execute_operation(MemeOperation::Mine {
            nonce: CryptoHash::from_str(
                "6e29f698682cedf788f02e2299e6428539dd40b8f262152473d4a6e6e6ee78a1",
            )
            .unwrap(),
        })
        .now_or_never()
        .expect("Execution of meme operation should not await anything");

    let _ = meme
        .execute_operation(MemeOperation::Mine {
            nonce: CryptoHash::from_str(
                "6e29f698682cedf788f02e2299e6428539dd40b8f262152473d4a6e6e6ee78a1",
            )
            .unwrap(),
        })
        .now_or_never()
        .expect("Execution of meme operation should not await anything");
}

#[tokio::test(flavor = "multi_thread")]
async fn operation_mine_enable_mining_supply_10000000() {
    let (mut meme, _state) = create_and_instantiate_meme(true, Some(Amount::from_tokens(10000000))).await;

    let _ = meme
        .execute_operation(MemeOperation::Mine {
            nonce: CryptoHash::from_str(
                "6e29f698682cedf788f02e2299e6428539dd40b8f262152473d4a6e6e6ee78a1",
            )
            .unwrap(),
        })
        .now_or_never()
        .expect("Execution of meme operation should not await anything");
}

#[tokio::test(flavor = "multi_thread")]
async fn operation_mine_enable_mining_supply_13000000() {
    let (mut meme, _state) = create_and_instantiate_meme(true, Some(Amount::from_tokens(13000000))).await;

    let _ = meme
        .execute_operation(MemeOperation::Mine {
            nonce: CryptoHash::from_str(
                "6e29f698682cedf788f02e2299e6428539dd40b8f262152473d4a6e6e6ee78a1",
            )
            .unwrap(),
        })
        .now_or_never()
        .expect("Execution of meme operation should not await anything");
}

#[tokio::test(flavor = "multi_thread")]
async fn user_chain_operation() {
    let (mut meme, _state) = create_and_instantiate_meme(false, None).await;
    let to = Account {
        chain_id: meme.runtime.borrow_mut().chain_id(),
        owner: AccountOwner::from_str(
            "0x02e900512d2fca22897f80a2f6932ff454f2752ef7afad18729dd25e5b5b6e03",
        )
        .unwrap(),
    };

    let response = meme
        .execute_operation(MemeOperation::Transfer {
            to,
            amount: Amount::from_tokens(1),
        })
        .now_or_never()
        .expect("Execution of meme operation should not await anything");

    assert!(matches!(response, MemeResponse::Ok));
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic(expected = "Invalid owner")]
async fn message_approve_meme_owner_self_insufficient_balance() {
    let (mut meme, state) = create_and_instantiate_meme(false, None).await;
    let mut runtime_context = ContractRuntimeAdapter::new(meme.runtime.clone());

    let from = runtime_context.authenticated_account();
    let amount = initial_owner_balance(&meme);
    let allowance = Amount::from_tokens(220);

    assert_eq!(balance_of(&state, from).await, amount);

    meme.execute_message(MemeMessage::Approve {
        owner: from,
        spender: from,
        amount: allowance,
    })
    .await;
}

#[tokio::test(flavor = "multi_thread")]
async fn message_transfer_ownership() {
    let (mut meme, state) = create_and_instantiate_meme(false, None).await;
    let mut runtime_context = ContractRuntimeAdapter::new(meme.runtime.clone());

    let owner = runtime_context.authenticated_account();
    let new_owner = Account {
        chain_id: meme.runtime.borrow_mut().chain_id(),
        owner: AccountOwner::from_str(
            "0x5279b3ae14d3b38e14b65a74aefe44824ea88b25c7841836e9ec77d991a5bc8f",
        )
        .unwrap(),
    };

    meme.execute_message(MemeMessage::TransferOwnership { owner, new_owner })
        .await;

    assert_eq!(owner_of(&state).await, new_owner);
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic(expected = "Authenticated caller ID has not been mocked")]
async fn operation_transfer_from_application_requires_authenticated_caller() {
    let (mut meme, _state) = create_and_instantiate_meme_with_config(CreateMemeConfig {
        authenticated_caller_id: None,
        ..default_create_meme_config()
    })
    .await;
    let to = Account {
        chain_id: meme.runtime.borrow_mut().chain_id(),
        owner: AccountOwner::from_str(
            "0x5279b3ae14d3b38e14b65a74aefe44824ea88b25c7841836e9ec77d991a5bc8f",
        )
        .unwrap(),
    };

    let _ = meme
        .execute_operation(MemeOperation::TransferFromApplication {
            to,
            amount: Amount::ONE,
        })
        .now_or_never()
        .expect("Execution of meme operation should not await anything");
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic]
async fn operation_initialize_liquidity_rejects_missing_caller() {
    let (mut meme, _state) = create_and_instantiate_meme_with_config(CreateMemeConfig {
        authenticated_caller_id: None,
        ..default_create_meme_config()
    })
    .await;
    let chain_id = meme.runtime.borrow_mut().chain_id();
    let pool_application = Account {
        chain_id,
        owner: AccountOwner::from_str(
            "0x5279b3ae14d3b38e14b65a74aefe44824ea88b25c7841836e9ec77d991a5bc8f",
        )
        .unwrap(),
    };

    let _ = meme
        .execute_operation(MemeOperation::InitializeLiquidity {
            pool_application,
            amount_0: Amount::from_tokens(1),
            pool_initialize: PoolInitializeLiquidityCall {
                amount_1_in: Amount::from_tokens(1),
                to: None,
            },
        })
        .await;
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic(expected = "Invalid caller")]
async fn message_initialize_liquidity_rejects_wrong_caller() {
    let (mut meme, _state) = create_and_instantiate_meme(false, None).await;
    let chain_id = meme.runtime.borrow_mut().chain_id();
    let wrong_caller = Account {
        chain_id,
        owner: AccountOwner::from_str(
            "0x02e900512d2fca22897f80a2f6932ff454f2752ef7afad18729dd25e5b5b6e03",
        )
        .unwrap(),
    };
    let to = Account {
        chain_id,
        owner: AccountOwner::from_str(
            "0x5279b3ae14d3b38e14b65a74aefe44824ea88b25c7841836e9ec77d991a5bc8f",
        )
        .unwrap(),
    };

    meme.execute_message(MemeMessage::InitializeLiquidity {
        caller: wrong_caller,
        pool_application: to,
        amount_0: Amount::from_tokens(1),
        pool_initialize: PoolInitializeLiquidityCall {
            amount_1_in: Amount::from_tokens(1),
            to: None,
        },
    })
    .await;
}

#[tokio::test(flavor = "multi_thread")]
async fn message_initialize_liquidity_duplicate_fails_without_double_transfer() {
    let (mut meme, state) = create_and_instantiate_meme(false, None).await;
    let chain_id = meme.runtime.borrow_mut().chain_id();
    let swap_application_id = swap_application_id_of(&state).await.unwrap();
    let caller = Account {
        chain_id,
        owner: AccountOwner::from(swap_application_id),
    };
    let application = application_account(&meme);
    let to = Account {
        chain_id,
        owner: AccountOwner::from_str(
            "0x02e900512d2fca22897f80a2f6932ff454f2752ef7afad18729dd25e5b5b6e03",
        )
        .unwrap(),
    };
    let liquidity = initial_liquidity();
    let amount = liquidity.fungible_amount;

    state
        .borrow_mut()
        .initialize_liquidity(liquidity, chain_id, false, None)
        .await
        .expect("Failed to initialize liquidity");

    meme.execute_message(MemeMessage::InitializeLiquidity {
        caller,
        pool_application: to,
        amount_0: amount,
        pool_initialize: PoolInitializeLiquidityCall {
            amount_1_in: Amount::from_tokens(1),
            to: None,
        },
    })
    .await;

    assert_eq!(balance_of(&state, to).await, amount);

    let second_attempt = std::panic::AssertUnwindSafe(async {
        meme.execute_message(MemeMessage::InitializeLiquidity {
            caller,
            pool_application: to,
            amount_0: amount,
            pool_initialize: PoolInitializeLiquidityCall {
                amount_1_in: Amount::from_tokens(1),
                to: None,
            },
        })
        .await;
    })
    .catch_unwind()
    .await;

    assert!(second_attempt.is_err());
    assert_eq!(balance_of(&state, to).await, amount);
    assert_eq!(allowance_of(&state, application, caller).await, Amount::ZERO);
}

#[tokio::test(flavor = "multi_thread")]
async fn operation_transfer_to_caller_returns_fail_on_insufficient_balance() {
    let (mut meme, state) = create_and_instantiate_meme(false, None).await;
    let chain_id = meme.runtime.borrow_mut().chain_id();
    meme.runtime
        .borrow_mut()
        .set_message_origin_chain_id(chain_id);

    let signer = Account {
        chain_id,
        owner: meme.runtime.borrow_mut().authenticated_signer().unwrap(),
    };
    let caller = application_account(&meme);
    let signer_balance = balance_of(&state, signer).await;
    let caller_balance = balance_of(&state, caller).await;
    let amount = signer_balance.try_add(Amount::ONE).unwrap();

    let response = meme
        .execute_operation(MemeOperation::TransferToCaller { amount })
        .now_or_never()
        .expect("Execution of meme operation should not await anything");

    assert!(matches!(response, MemeResponse::Fail(_)));
    assert_eq!(balance_of(&state, signer).await, signer_balance);
    assert_eq!(balance_of(&state, caller).await, caller_balance);
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic(expected = "Not allowed")]
async fn message_mint_rejects_non_owner_signer() {
    let (mut meme, _state) = create_and_instantiate_meme_with_config(CreateMemeConfig {
        authenticated_signer: AccountOwner::from_str(
            "0x02e900512d2fca22897f80a2f6932ff454f2752ef7afad18729dd25e5b5b6e03",
        )
        .unwrap(),
        ..default_create_meme_config()
    })
    .await;

    let to = Account {
        chain_id: meme.runtime.borrow_mut().chain_id(),
        owner: AccountOwner::from_str(
            "0x5279b3ae14d3b38e14b65a74aefe44824ea88b25c7841836e9ec77d991a5bc8f",
        )
        .unwrap(),
    };

    meme.execute_message(MemeMessage::Mint {
        to,
        amount: Amount::ONE,
    })
    .await;
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic(expected = "Invalid receipt result")]
async fn operation_transfer_from_application_with_receipt_rejects_completed_receipt() {
    let (mut meme, _state) = create_and_instantiate_meme(false, None).await;
    let to = alternate_account(meme.runtime.borrow_mut().chain_id());

    let _ = meme
        .execute_operation(MemeOperation::TransferFromApplicationWithReceipt {
            to,
            amount: Amount::from_tokens(5),
            receipt: pool_claim_receipt(Some(Ok(()))),
        })
        .await;
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic(expected = "Invalid receipt amount")]
async fn operation_transfer_from_application_with_receipt_rejects_amount_mismatch() {
    let (mut meme, _state) = create_and_instantiate_meme(false, None).await;
    let to = alternate_account(meme.runtime.borrow_mut().chain_id());

    let _ = meme
        .execute_operation(MemeOperation::TransferFromApplicationWithReceipt {
            to,
            amount: Amount::from_tokens(6),
            receipt: pool_claim_receipt(None),
        })
        .await;
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic(expected = "Authenticated caller ID has not been mocked")]
async fn operation_transfer_from_application_with_receipt_rejects_missing_caller() {
    let (mut meme, _state) = create_and_instantiate_meme_with_config(CreateMemeConfig {
        authenticated_caller_id: None,
        ..default_create_meme_config()
    })
    .await;
    let to = alternate_account(meme.runtime.borrow_mut().chain_id());

    let _ = meme
        .execute_operation(MemeOperation::TransferFromApplicationWithReceipt {
            to,
            amount: Amount::from_tokens(5),
            receipt: pool_claim_receipt(None),
        })
        .await;
}

#[tokio::test(flavor = "multi_thread")]
async fn message_transfer_from_application_with_receipt_success_sends_success_receipt() {
    let (mut meme, state) = create_and_instantiate_meme(false, None).await;
    let caller = application_account(&mut meme);
    let to = alternate_account(meme.runtime.borrow_mut().chain_id());
    let amount = Amount::from_tokens(5);
    let caller_balance = balance_of(&state, caller).await;
    let to_balance = balance_of(&state, to).await;

    meme.runtime.borrow_mut().set_message_is_bouncing(false);
    meme.execute_message(MemeMessage::TransferFromApplicationWithReceipt {
        caller,
        to,
        amount,
        receipt: pool_claim_receipt(None),
    })
    .await;

    assert_eq!(
        balance_of(&state, caller).await,
        caller_balance.try_sub(amount).unwrap()
    );
    assert_eq!(
        balance_of(&state, to).await,
        to_balance.try_add(amount).unwrap()
    );
    assert_transfer_from_application_receipt(&meme, caller, Ok(()));
}

#[tokio::test(flavor = "multi_thread")]
async fn message_transfer_from_application_with_receipt_fail_sends_fail_receipt() {
    let (mut meme, state) = create_and_instantiate_meme(false, None).await;
    let caller = application_account(&mut meme);
    let to = alternate_account(meme.runtime.borrow_mut().chain_id());
    let amount = balance_of(&state, caller)
        .await
        .try_add(Amount::ONE)
        .unwrap();
    let caller_balance = balance_of(&state, caller).await;
    let to_balance = balance_of(&state, to).await;

    meme.runtime.borrow_mut().set_message_is_bouncing(false);
    meme.execute_message(MemeMessage::TransferFromApplicationWithReceipt {
        caller,
        to,
        amount,
        receipt: TransferFromApplicationReceipt {
            amount,
            ..pool_claim_receipt(None)
        },
    })
    .await;

    assert_eq!(balance_of(&state, caller).await, caller_balance);
    assert_eq!(balance_of(&state, to).await, to_balance);
    assert_transfer_from_application_receipt_err(&meme, caller);
}

#[tokio::test(flavor = "multi_thread")]
async fn message_transfer_from_application_with_receipt_bounce_sends_fail_receipt_without_transfer()
{
    let (mut meme, state) = create_and_instantiate_meme(false, None).await;
    let caller = application_account(&mut meme);
    let to = alternate_account(meme.runtime.borrow_mut().chain_id());
    let amount = Amount::from_tokens(5);
    let caller_balance = balance_of(&state, caller).await;
    let to_balance = balance_of(&state, to).await;

    meme.runtime.borrow_mut().set_message_is_bouncing(true);
    meme.execute_message(MemeMessage::TransferFromApplicationWithReceipt {
        caller,
        to,
        amount,
        receipt: pool_claim_receipt(None),
    })
    .await;

    assert_eq!(balance_of(&state, caller).await, caller_balance);
    assert_eq!(balance_of(&state, to).await, to_balance);
    assert_transfer_from_application_receipt_err(&meme, caller);
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic(expected = "Invalid receipt result")]
async fn message_transfer_from_application_with_receipt_rejects_completed_receipt() {
    let (mut meme, _state) = create_and_instantiate_meme(false, None).await;
    let caller = application_account(&mut meme);
    let to = alternate_account(meme.runtime.borrow_mut().chain_id());
    meme.runtime.borrow_mut().set_message_is_bouncing(false);

    meme.execute_message(MemeMessage::TransferFromApplicationWithReceipt {
        caller,
        to,
        amount: Amount::from_tokens(5),
        receipt: pool_claim_receipt(Some(Ok(()))),
    })
    .await;
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic(expected = "Invalid receipt amount")]
async fn message_transfer_from_application_with_receipt_rejects_amount_mismatch() {
    let (mut meme, _state) = create_and_instantiate_meme(false, None).await;
    let caller = application_account(&mut meme);
    let to = alternate_account(meme.runtime.borrow_mut().chain_id());
    meme.runtime.borrow_mut().set_message_is_bouncing(false);

    meme.execute_message(MemeMessage::TransferFromApplicationWithReceipt {
        caller,
        to,
        amount: Amount::from_tokens(6),
        receipt: pool_claim_receipt(None),
    })
    .await;
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic(expected = "Invalid receipt result")]
async fn message_transfer_from_application_receipt_rejects_incomplete_receipt() {
    let (mut meme, _state) = create_and_instantiate_meme(false, None).await;
    let caller = pool_application_account(meme.runtime.borrow_mut().chain_id());

    meme.runtime.borrow_mut().set_message_is_bouncing(false);

    meme.execute_message(MemeMessage::TransferFromApplicationReceipt {
        caller,
        receipt: pool_claim_receipt(None),
    })
    .await;
}

#[tokio::test(flavor = "multi_thread")]
async fn message_transfer_from_application_receipt_dispatches_pool_claim_success() {
    let (mut meme, _state) = create_and_instantiate_meme(false, None).await;
    let caller = pool_application_account(meme.runtime.borrow_mut().chain_id());
    let owner = alternate_account(meme.runtime.borrow_mut().chain_id());
    let receipt = TransferFromApplicationReceipt {
        owner,
        result: Some(Ok(())),
        ..pool_claim_receipt(None)
    };

    meme.runtime.borrow_mut().set_message_is_bouncing(false);

    let captured = std::rc::Rc::new(std::cell::RefCell::new(None));
    let captured_for_handler = captured.clone();
    meme.runtime.borrow_mut().set_call_application_handler(
        move |_authenticated, application_id, operation| {
            *captured_for_handler.borrow_mut() = Some((application_id, operation));
            bcs::to_bytes(&PoolResponse::Ok).unwrap()
        },
    );

    meme.execute_message(MemeMessage::TransferFromApplicationReceipt {
        caller,
        receipt: receipt.clone(),
    })
    .await;

    let (application_id, operation) = captured.borrow().clone().unwrap();
    let AccountOwner::Address32(application_description_hash) = caller.owner else {
        panic!("Invalid test caller");
    };
    assert_eq!(
        application_id,
        ApplicationId::new(application_description_hash)
    );
    assert!(matches!(
        bcs::from_bytes::<PoolOperation>(&operation).unwrap(),
        PoolOperation::ClaimTransferReceipt {
            receipt: ClaimTransferReceipt {
                owner: receipt_owner,
                token: receipt_token,
                amount: receipt_amount,
                result: Ok(()),
            },
        } if receipt_owner == owner
            && receipt_token == receipt.token
            && receipt_amount == receipt.amount
    ));
}

#[tokio::test(flavor = "multi_thread")]
async fn message_transfer_from_application_receipt_dispatches_pool_claim_fail() {
    let (mut meme, _state) = create_and_instantiate_meme(false, None).await;
    let caller = pool_application_account(meme.runtime.borrow_mut().chain_id());
    let receipt = TransferFromApplicationReceipt {
        result: Some(Err("failed".to_string())),
        ..pool_claim_receipt(None)
    };

    meme.runtime.borrow_mut().set_message_is_bouncing(false);

    let captured = std::rc::Rc::new(std::cell::RefCell::new(None));
    let captured_for_handler = captured.clone();
    meme.runtime.borrow_mut().set_call_application_handler(
        move |_authenticated, application_id, operation| {
            *captured_for_handler.borrow_mut() = Some((application_id, operation));
            bcs::to_bytes(&PoolResponse::Ok).unwrap()
        },
    );

    meme.execute_message(MemeMessage::TransferFromApplicationReceipt {
        caller,
        receipt: receipt.clone(),
    })
    .await;

    let (_application_id, operation) = captured.borrow().clone().unwrap();
    assert!(matches!(
        bcs::from_bytes::<PoolOperation>(&operation).unwrap(),
        PoolOperation::ClaimTransferReceipt {
            receipt: ClaimTransferReceipt {
                result: Err(error), ..
            },
        } if error == "failed"
    ));
}

#[tokio::test(flavor = "multi_thread")]
async fn message_transfer_from_application_receipt_dispatches_pool_add_liquidity_success() {
    let (mut meme, _state) = create_and_instantiate_meme(false, None).await;
    let caller = pool_application_account(meme.runtime.borrow_mut().chain_id());
    let receipt = pool_add_liquidity_receipt(Some(Ok(())), FundType::AddLiquidity);

    meme.runtime.borrow_mut().set_message_is_bouncing(false);

    let captured = std::rc::Rc::new(std::cell::RefCell::new(None));
    let captured_for_handler = captured.clone();
    meme.runtime.borrow_mut().set_call_application_handler(
        move |_authenticated, application_id, operation| {
            *captured_for_handler.borrow_mut() = Some((application_id, operation));
            bcs::to_bytes(&PoolResponse::Ok).unwrap()
        },
    );

    meme.execute_message(MemeMessage::TransferFromApplicationReceipt {
        caller,
        receipt: receipt.clone(),
    })
    .await;

    let (_application_id, operation) = captured.borrow().clone().unwrap();
    assert!(matches!(
        bcs::from_bytes::<PoolOperation>(&operation).unwrap(),
        PoolOperation::AddLiquidityTransferReceipt { receipt: transfer_receipt }
            if transfer_receipt.result == Ok(())
                && transfer_receipt.request.amount_in == receipt.amount
                && transfer_receipt.request.fund_type == FundType::AddLiquidity
    ));
}

#[tokio::test(flavor = "multi_thread")]
async fn message_transfer_from_application_receipt_dispatches_pool_swap_success() {
    let (mut meme, _state) = create_and_instantiate_meme(false, None).await;
    let caller = pool_application_account(meme.runtime.borrow_mut().chain_id());
    let receipt = pool_swap_receipt(Some(Ok(())), FundType::Swap);

    meme.runtime.borrow_mut().set_message_is_bouncing(false);

    let captured = std::rc::Rc::new(std::cell::RefCell::new(None));
    let captured_for_handler = captured.clone();
    meme.runtime.borrow_mut().set_call_application_handler(
        move |_authenticated, application_id, operation| {
            *captured_for_handler.borrow_mut() = Some((application_id, operation));
            bcs::to_bytes(&PoolResponse::Ok).unwrap()
        },
    );

    meme.execute_message(MemeMessage::TransferFromApplicationReceipt {
        caller,
        receipt: receipt.clone(),
    })
    .await;

    let (_application_id, operation) = captured.borrow().clone().unwrap();
    assert!(matches!(
        bcs::from_bytes::<PoolOperation>(&operation).unwrap(),
        PoolOperation::SwapTransferReceipt { receipt: transfer_receipt }
            if transfer_receipt.result == Ok(())
                && transfer_receipt.request.amount_in == receipt.amount
                && transfer_receipt.request.fund_type == FundType::Swap
    ));
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic(expected = "Invalid receipt payload")]
async fn message_transfer_from_application_receipt_rejects_pool_add_liquidity_payload_mismatch() {
    let (mut meme, _state) = create_and_instantiate_meme(false, None).await;
    let caller = pool_application_account(meme.runtime.borrow_mut().chain_id());
    let mut receipt = pool_add_liquidity_receipt(Some(Ok(())), FundType::AddLiquidity);
    receipt.payload = pool_swap_receipt(Some(Ok(())), FundType::Swap).payload;

    meme.runtime.borrow_mut().set_message_is_bouncing(false);

    meme.execute_message(MemeMessage::TransferFromApplicationReceipt { caller, receipt })
        .await;
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic(expected = "Invalid receipt payload")]
async fn message_transfer_from_application_receipt_rejects_pool_swap_payload_mismatch() {
    let (mut meme, _state) = create_and_instantiate_meme(false, None).await;
    let caller = pool_application_account(meme.runtime.borrow_mut().chain_id());
    let mut receipt = pool_swap_receipt(Some(Ok(())), FundType::Swap);
    receipt.payload = pool_add_liquidity_receipt(Some(Ok(())), FundType::AddLiquidity).payload;

    meme.runtime.borrow_mut().set_message_is_bouncing(false);

    meme.execute_message(MemeMessage::TransferFromApplicationReceipt { caller, receipt })
        .await;
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic(expected = "Invalid fund type")]
async fn message_transfer_from_application_receipt_rejects_pool_add_liquidity_wrong_fund_type() {
    let (mut meme, _state) = create_and_instantiate_meme(false, None).await;
    let caller = pool_application_account(meme.runtime.borrow_mut().chain_id());
    let receipt = pool_add_liquidity_receipt(Some(Ok(())), FundType::Swap);

    meme.runtime.borrow_mut().set_message_is_bouncing(false);

    meme.execute_message(MemeMessage::TransferFromApplicationReceipt { caller, receipt })
        .await;
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic(expected = "Invalid fund type")]
async fn message_transfer_from_application_receipt_rejects_pool_swap_wrong_fund_type() {
    let (mut meme, _state) = create_and_instantiate_meme(false, None).await;
    let caller = pool_application_account(meme.runtime.borrow_mut().chain_id());
    let receipt = pool_swap_receipt(Some(Ok(())), FundType::AddLiquidity);

    meme.runtime.borrow_mut().set_message_is_bouncing(false);

    meme.execute_message(MemeMessage::TransferFromApplicationReceipt { caller, receipt })
        .await;
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic(expected = "Invalid receipt caller")]
async fn message_transfer_from_application_receipt_rejects_invalid_caller_owner() {
    let (mut meme, _state) = create_and_instantiate_meme(false, None).await;
    let caller = Account {
        chain_id: meme.runtime.borrow_mut().chain_id(),
        owner: AccountOwner::CHAIN,
    };

    meme.runtime.borrow_mut().set_message_is_bouncing(false);

    meme.execute_message(MemeMessage::TransferFromApplicationReceipt {
        caller,
        receipt: pool_claim_receipt(Some(Ok(()))),
    })
    .await;
}

#[tokio::test(flavor = "multi_thread")]
async fn message_transfer_from_application_receipt_bounce_is_noop() {
    let (mut meme, _state) = create_and_instantiate_meme(false, None).await;
    let caller = pool_application_account(meme.runtime.borrow_mut().chain_id());

    meme.runtime.borrow_mut().set_message_is_bouncing(true);
    meme.execute_message(MemeMessage::TransferFromApplicationReceipt {
        caller,
        receipt: pool_claim_receipt(Some(Ok(()))),
    })
    .await;
}

#[tokio::test(flavor = "multi_thread")]
async fn message_transfer_from_application_receipt_bounce_does_not_dispatch_pool_settlement() {
    let (mut meme, _state) = create_and_instantiate_meme(false, None).await;
    let caller = pool_application_account(meme.runtime.borrow_mut().chain_id());

    let captured = std::rc::Rc::new(std::cell::RefCell::new(None));
    let captured_for_handler = captured.clone();
    meme.runtime.borrow_mut().set_call_application_handler(
        move |_authenticated, application_id, operation| {
            *captured_for_handler.borrow_mut() = Some((application_id, operation));
            bcs::to_bytes(&PoolResponse::Ok).unwrap()
        },
    );

    meme.runtime.borrow_mut().set_message_is_bouncing(true);
    meme.execute_message(MemeMessage::TransferFromApplicationReceipt {
        caller,
        receipt: pool_claim_receipt(Some(Ok(()))),
    })
    .await;

    assert!(captured.borrow().is_none());
}

#[tokio::test(flavor = "multi_thread")]
async fn message_redeem_none_redeems_full_balance_to_owner_account() {
    let (mut meme, state) = create_and_instantiate_meme(false, None).await;
    let creator_chain_id = meme.runtime.borrow_mut().chain_id();
    let remote_owner = Account {
        chain_id: ChainId::from_str(
            "aee928d4bf3880353b4a3cd9b6f88e6cc6e5ed050860abae439e7782e9b2dfe8",
        )
        .unwrap(),
        owner: meme.runtime.borrow_mut().authenticated_signer().unwrap(),
    };
    let creator_owner = Account {
        chain_id: creator_chain_id,
        owner: remote_owner.owner,
    };
    let creator_balance = balance_of(&state, creator_owner).await;

    meme.execute_message(MemeMessage::Redeem {
        owner: remote_owner,
        amount: None,
    })
    .await;

    assert_eq!(balance_of(&state, creator_owner).await, Amount::ZERO);
    assert_eq!(balance_of(&state, remote_owner).await, creator_balance);
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic(expected = "Invalid amount")]
async fn message_redeem_zero_amount_rejected() {
    let (mut meme, _state) = create_and_instantiate_meme(false, None).await;
    let remote_owner = Account {
        chain_id: ChainId::from_str(
            "aee928d4bf3880353b4a3cd9b6f88e6cc6e5ed050860abae439e7782e9b2dfe8",
        )
        .unwrap(),
        owner: meme.runtime.borrow_mut().authenticated_signer().unwrap(),
    };

    meme.execute_message(MemeMessage::Redeem {
        owner: remote_owner,
        amount: Some(Amount::ZERO),
    })
    .await;
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic(expected = "Insufficient funds")]
async fn message_redeem_rejects_amount_above_balance() {
    let (mut meme, state) = create_and_instantiate_meme(false, None).await;
    let creator_chain_id = meme.runtime.borrow_mut().chain_id();
    let remote_owner = Account {
        chain_id: ChainId::from_str(
            "aee928d4bf3880353b4a3cd9b6f88e6cc6e5ed050860abae439e7782e9b2dfe8",
        )
        .unwrap(),
        owner: meme.runtime.borrow_mut().authenticated_signer().unwrap(),
    };
    let creator_owner = Account {
        chain_id: creator_chain_id,
        owner: remote_owner.owner,
    };
    let creator_balance = balance_of(&state, creator_owner).await;

    meme.execute_message(MemeMessage::Redeem {
        owner: remote_owner,
        amount: Some(creator_balance.try_add(Amount::ONE).unwrap()),
    })
    .await;
}

// ---------------------------------------------------------------------------
// Crash tests: same scenarios as above but with a different valid nonce.
// These are migrated from `meme/src/contract_tests/crash.rs`.
// ---------------------------------------------------------------------------

#[tokio::test(flavor = "multi_thread")]
#[should_panic(expected = "Not enabled")]
async fn crash_operation_mine_not_enable_mining() {
    let (mut meme, _state) = create_and_instantiate_crash_meme(false, None).await;

    let _ = meme
        .execute_operation(MemeOperation::Mine {
            nonce: CryptoHash::new(&TestString::new("aaaa")),
        })
        .now_or_never()
        .expect("Execution of meme operation should not await anything");
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic(expected = "Invalid nonce")]
async fn crash_operation_mine_enable_mining_supply_none_invalid_nonce() {
    let (mut meme, _state) = create_and_instantiate_crash_meme(true, None).await;

    let _ = meme
        .execute_operation(MemeOperation::Mine {
            nonce: CryptoHash::new(&TestString::new("aaaa")),
        })
        .now_or_never()
        .expect("Execution of meme operation should not await anything");
}

#[tokio::test(flavor = "multi_thread")]
async fn crash_operation_mine_enable_mining_supply_none_one_block() {
    let (mut meme, _state) = create_and_instantiate_crash_meme(true, None).await;

    let _ = meme
        .execute_operation(MemeOperation::Mine {
            nonce: CryptoHash::from_str(
                "6e29f698682cedf788f02e2299e6428539dd40b8f262152473d4a6e6e6e4ccff",
            )
            .unwrap(),
        })
        .now_or_never()
        .expect("Execution of meme operation should not await anything");

    // TODO: check reward balance
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic(expected = "Stale block height")]
async fn crash_operation_mine_enable_mining_supply_none_two_block() {
    let (mut meme, _state) = create_and_instantiate_crash_meme(true, None).await;

    let _ = meme
        .execute_operation(MemeOperation::Mine {
            nonce: CryptoHash::from_str(
                "6e29f698682cedf788f02e2299e6428539dd40b8f262152473d4a6e6e6e4ccff",
            )
            .unwrap(),
        })
        .now_or_never()
        .expect("Execution of meme operation should not await anything");

    let _ = meme
        .execute_operation(MemeOperation::Mine {
            nonce: CryptoHash::from_str(
                "6e29f698682cedf788f02e2299e6428539dd40b8f262152473d4a6e6e6e4ccff",
            )
            .unwrap(),
        })
        .now_or_never()
        .expect("Execution of meme operation should not await anything");
}

#[tokio::test(flavor = "multi_thread")]
async fn crash_operation_mine_enable_mining_supply_10000000() {
    let (mut meme, _state) = create_and_instantiate_crash_meme(true, Some(Amount::from_tokens(10000000))).await;

    let _ = meme
        .execute_operation(MemeOperation::Mine {
            nonce: CryptoHash::from_str(
                "6e29f698682cedf788f02e2299e6428539dd40b8f262152473d4a6e6e6e4ccff",
            )
            .unwrap(),
        })
        .now_or_never()
        .expect("Execution of meme operation should not await anything");
}

#[tokio::test(flavor = "multi_thread")]
async fn crash_operation_mine_enable_mining_supply_13000000() {
    let (mut meme, _state) = create_and_instantiate_crash_meme(true, Some(Amount::from_tokens(13000000))).await;

    let _ = meme
        .execute_operation(MemeOperation::Mine {
            nonce: CryptoHash::from_str(
                "6e29f698682cedf788f02e2299e6428539dd40b8f262152473d4a6e6e6e4ccff",
            )
            .unwrap(),
        })
        .now_or_never()
        .expect("Execution of meme operation should not await anything");
}

#[tokio::test(flavor = "multi_thread")]
async fn crash_user_chain_operation() {
    let (mut meme, _state) = create_and_instantiate_crash_meme(false, None).await;
    let to = Account {
        chain_id: meme.runtime.borrow_mut().chain_id(),
        owner: AccountOwner::from_str(
            "0x02e900512d2fca22897f80a2f6932ff454f2752ef7afad18729dd25e5b5b6e03",
        )
        .unwrap(),
    };

    let response = meme
        .execute_operation(MemeOperation::Transfer {
            to,
            amount: Amount::from_tokens(1),
        })
        .now_or_never()
        .expect("Execution of meme operation should not await anything");

    assert!(matches!(response, MemeResponse::Ok));
}

#[tokio::test(flavor = "multi_thread")]
async fn crash_message_transfer() {
    let (mut meme, state) = create_and_instantiate_crash_meme(false, None).await;
    let mut runtime_context = ContractRuntimeAdapter::new(meme.runtime.clone());

    let from = runtime_context.authenticated_account();
    let amount = initial_owner_balance(&meme);

    let to = Account {
        chain_id: runtime_context.chain_id(),
        owner: AccountOwner::from_str(
            "0x5279b3ae14d3b38e14b65a74aefe44824ea88b25c7841836e9ec77d991a5bc8f",
        )
        .unwrap(),
    };

    assert_eq!(balance_of(&state, from).await, amount);

    meme.execute_message(MemeMessage::Transfer { from, to, amount })
        .await;

    assert_eq!(balance_of(&state, from).await, Amount::ZERO);
    assert_eq!(balance_of(&state, to).await, amount);
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic(expected = "Insufficient funds")]
async fn crash_message_transfer_insufficient_funds() {
    let (mut meme, state) = create_and_instantiate_crash_meme(false, None).await;
    let mut runtime_context = ContractRuntimeAdapter::new(meme.runtime.clone());

    let from = runtime_context.authenticated_account();
    let amount = initial_owner_balance(&meme);
    let transfer_amount = amount.try_add(Amount::ONE).unwrap();

    let to = Account {
        chain_id: runtime_context.chain_id(),
        owner: AccountOwner::from_str(
            "0x5279b3ae14d3b38e14b65a74aefe44824ea88b25c7841836e9ec77d991a5bc8f",
        )
        .unwrap(),
    };

    assert_eq!(balance_of(&state, from).await, amount);

    meme.execute_message(MemeMessage::Transfer {
        from,
        to,
        amount: transfer_amount,
    })
    .await;
}

#[tokio::test(flavor = "multi_thread")]
async fn crash_message_approve_owner_success() {
    let (mut meme, state) = create_and_instantiate_crash_meme(false, None).await;
    let mut runtime_context = ContractRuntimeAdapter::new(meme.runtime.clone());

    let from = runtime_context.authenticated_account();
    let amount = initial_owner_balance(&meme);
    let allowance = Amount::from_tokens(22);

    let spender = Account {
        chain_id: runtime_context.chain_id(),
        owner: AccountOwner::from_str(
            "0x5279b3ae14d3b38e14b65a74aefe44824ea88b25c7841836e9ec77d991a5bc8f",
        )
        .unwrap(),
    };

    assert_eq!(balance_of(&state, from).await, amount);

    meme.execute_message(MemeMessage::Approve {
        owner: from,
        spender,
        amount: allowance,
    })
    .await;

    assert_eq!(balance_of(&state, from).await, amount.try_sub(allowance).unwrap());
    assert_eq!(allowance_of(&state, from, spender).await, allowance);

    meme.execute_message(MemeMessage::Approve {
        owner: from,
        spender,
        amount: allowance,
    })
    .await;

    assert_eq!(
        balance_of(&state, from).await,
        amount.try_sub(allowance).unwrap().try_sub(allowance).unwrap()
    );
    assert_eq!(allowance_of(&state, from, spender).await, allowance.try_mul(2).unwrap());

    let to = Account {
        chain_id: runtime_context.chain_id(),
        owner: AccountOwner::from_str(
            "0x02e900512d2fca22897f80a2f6932ff454f2752ef7afad18729dd25e5b5b6e08",
        )
        .unwrap(),
    };

    meme.execute_message(MemeMessage::TransferFrom {
        owner: spender,
        from,
        to,
        amount: allowance,
    })
    .await;

    assert_eq!(allowance_of(&state, from, spender).await, allowance);
    assert_eq!(balance_of(&state, to).await, allowance);
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic(expected = "Insufficient funds")]
async fn crash_message_approve_insufficient_balance() {
    let (mut meme, state) = create_and_instantiate_crash_meme(false, None).await;
    let mut runtime_context = ContractRuntimeAdapter::new(meme.runtime.clone());

    let from = runtime_context.authenticated_account();
    let amount = initial_owner_balance(&meme);
    let allowance = Amount::from_tokens(220);

    let spender = Account {
        chain_id: runtime_context.chain_id(),
        owner: AccountOwner::from_str(
            "0x5279b3ae14d3b38e14b65a74aefe44824ea88b25c7841836e9ec77d991a5bc8f",
        )
        .unwrap(),
    };

    assert_eq!(balance_of(&state, from).await, amount);

    meme.execute_message(MemeMessage::Approve {
        owner: from,
        spender,
        amount: allowance,
    })
    .await;
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic(expected = "Invalid owner")]
async fn crash_message_approve_meme_owner_self_insufficient_balance() {
    let (mut meme, state) = create_and_instantiate_crash_meme(false, None).await;
    let mut runtime_context = ContractRuntimeAdapter::new(meme.runtime.clone());

    let from = runtime_context.authenticated_account();
    let amount = initial_owner_balance(&meme);
    let allowance = Amount::from_tokens(220);

    assert_eq!(balance_of(&state, from).await, amount);

    meme.execute_message(MemeMessage::Approve {
        owner: from,
        spender: from,
        amount: allowance,
    })
    .await;
}

#[tokio::test(flavor = "multi_thread")]
async fn crash_message_transfer_ownership() {
    let (mut meme, state) = create_and_instantiate_crash_meme(false, None).await;
    let mut runtime_context = ContractRuntimeAdapter::new(meme.runtime.clone());

    let owner = runtime_context.authenticated_account();
    let new_owner = Account {
        chain_id: meme.runtime.borrow_mut().chain_id(),
        owner: AccountOwner::from_str(
            "0x5279b3ae14d3b38e14b65a74aefe44824ea88b25c7841836e9ec77d991a5bc8f",
        )
        .unwrap(),
    };

    meme.execute_message(MemeMessage::TransferOwnership { owner, new_owner })
        .await;

    assert_eq!(owner_of(&state).await, new_owner);
}

const DEFAULT_OPERATOR: &str =
    "0xfd90bbb496d286ff1227b8aa2f0d8e479d2b425257940bf36c4338ab73705ac6";
const DEFAULT_CHAIN_ID: &str =
    "abdb7c1079f36eaa03f629540283a881eb4256d1ece83a84415022d4d2a9ac65";

const CRASH_OPERATOR: &str =
    "0xf3989fdc1402acf54fac6b2914589f689a78b5356107503348b9654639b35b07";
const CRASH_CHAIN_ID: &str =
    "500d98c79457cf58256784f585a8dd0c8f9da70ee6b73b032b2e793583a83dcb";

struct CreateMemeConfig {
    enable_mining: bool,
    mining_supply: Option<Amount>,
    operator: AccountOwner,
    chain_id: ChainId,
    authenticated_caller_id: Option<ApplicationId>,
    authenticated_signer: AccountOwner,
    block_height: BlockHeight,
}

fn default_create_meme_config() -> CreateMemeConfig {
    CreateMemeConfig {
        enable_mining: false,
        mining_supply: None,
        operator: AccountOwner::from_str(DEFAULT_OPERATOR).unwrap(),
        chain_id: ChainId::from_str(DEFAULT_CHAIN_ID).unwrap(),
        authenticated_caller_id: Some(
            ApplicationId::from_str(
                "b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bad",
            )
            .unwrap(),
        ),
        authenticated_signer: AccountOwner::from_str(DEFAULT_OPERATOR).unwrap(),
        block_height: BlockHeight(0),
    }
}

fn crash_create_meme_config() -> CreateMemeConfig {
    CreateMemeConfig {
        operator: AccountOwner::from_str(CRASH_OPERATOR).unwrap(),
        chain_id: ChainId::from_str(CRASH_CHAIN_ID).unwrap(),
        authenticated_signer: AccountOwner::from_str(CRASH_OPERATOR).unwrap(),
        ..default_create_meme_config()
    }
}

async fn create_and_instantiate_meme(
    enable_mining: bool,
    mining_supply: Option<Amount>,
) -> (MemeContract, Rc<RefCell<StateAppState>>) {
    let mut config = default_create_meme_config();
    config.enable_mining = enable_mining;
    config.mining_supply = mining_supply;
    create_and_instantiate_meme_with_config(config).await
}

async fn create_and_instantiate_crash_meme(
    enable_mining: bool,
    mining_supply: Option<Amount>,
) -> (MemeContract, Rc<RefCell<StateAppState>>) {
    let mut config = crash_create_meme_config();
    config.enable_mining = enable_mining;
    config.mining_supply = mining_supply;
    create_and_instantiate_meme_with_config(config).await
}

async fn create_and_instantiate_meme_with_config(
    config: CreateMemeConfig,
) -> (MemeContract, Rc<RefCell<StateAppState>>) {
    let operator = config.operator;
    let chain_id = config.chain_id;
    let owner = Account {
        chain_id,
        owner: operator,
    };

    let application_id =
        ApplicationId::from_str("b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bad")
            .unwrap()
            .with_abi::<MemeAbi>();

    let swap_application_id =
        ApplicationId::from_str("b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bae")
            .unwrap();

    let initial_supply = Amount::from_tokens(21000000);
    let parameters = MemeParameters {
        creator: owner,
        initial_liquidity: Some(Liquidity {
            fungible_amount: Amount::from_tokens(11000000),
            native_amount: Amount::from_tokens(10),
        }),
        virtual_initial_liquidity: true,
        swap_creator_chain_id: chain_id,
        enable_mining: config.enable_mining,
        mining_supply: config.mining_supply,
    };

    let mut runtime = ContractRuntime::new()
        .with_can_change_application_permissions(true)
        .with_chain_id(chain_id)
        .with_application_id(application_id)
        .with_chain_ownership(ChainOwnership::single(operator))
        .with_owner_balance(
            AccountOwner::from(application_id.forget_abi()),
            Amount::from_tokens(10000),
        )
        .with_owner_balance(operator, Amount::from_tokens(10000))
        .with_owner_balance(config.authenticated_signer, Amount::from_tokens(10000))
        .with_owner_balance(AccountOwner::from(swap_application_id), Amount::ZERO)
        .with_chain_balance(Amount::ONE)
        .with_application_creator_chain_id(chain_id)
        .with_application_parameters(parameters.clone())
        .with_system_time(Timestamp::now())
        .with_block_height(config.block_height)
        .with_authenticated_signer(config.authenticated_signer);

    if let Some(authenticated_caller_id) = config.authenticated_caller_id {
        runtime = runtime.with_authenticated_caller_id(authenticated_caller_id);
    }

    let mut contract = MemeContract {
        state: Rc::new(RefCell::new(
            BusinessState::load(runtime.root_view_storage_context())
                .blocking_wait()
                .expect("Failed to read from mock key value store"),
        )),
        runtime: Rc::new(RefCell::new(runtime)),
    };

    let instantiation_argument = InstantiationArgument {
        meme: Meme {
            name: "Test Token".to_string(),
            ticker: "LTT".to_string(),
            decimals: 6,
            initial_supply,
            total_supply: initial_supply,
            metadata: Metadata {
                logo_store_type: StoreType::S3,
                logo: Some(CryptoHash::new(&TestString::new("Test Logo".to_string()))),
                description: "Test token description".to_string(),
                twitter: None,
                telegram: None,
                discord: None,
                website: None,
                github: None,
                live_stream: None,
            },
            virtual_initial_liquidity: true,
            initial_liquidity: parameters.initial_liquidity,
        },
        blob_gateway_application_id: None,
        ams_application_id: None,
        proxy_application_id: Some(application_id.forget_abi()),
        swap_application_id: Some(swap_application_id),
    };

    contract.instantiate(instantiation_argument.clone()).await;

    // Set up a real state app behind the mock call_application handler.
    let state_app_state = Rc::new(RefCell::new(
        StateAppState::load(contract.runtime.borrow_mut().root_view_storage_context())
            .blocking_wait()
            .expect("Failed to load meme state v1"),
    ));
    state_app_state.borrow_mut().instantiate(StateInstantiationArgument {
        business_application_id: application_id.forget_abi(),
        operator: Some(owner),
        proxy_application_id: Some(application_id.forget_abi()),
    });

    // Manually append the state app to the business app state.
    contract
        .state
        .borrow_mut()
        .state_applications
        .insert(&1, application_id.forget_abi())
        .unwrap();
    contract.state.borrow_mut().latest_state_version.set(1);

    let state_app_state_for_handler = state_app_state.clone();
    contract
        .runtime
        .borrow_mut()
        .set_call_application_handler(move |_authenticated, app_id, operation| {
            if app_id != application_id.forget_abi() {
                return mock_non_state_application_call(_authenticated, app_id, &operation);
            }
            dispatch_state_operation(
                &mut state_app_state_for_handler.borrow_mut(),
                &operation,
            )
        });

    // Initialize the meme state via the business app (business app acts as its own proxy in tests).
    let argument = InitializeArgument {
        owner,
        holder: Account {
            chain_id,
            owner: AccountOwner::from(application_id.forget_abi()),
        },
        meme: instantiation_argument.meme,
        initial_owner_balance: Amount::from_tokens(100),
        blob_gateway_application_id: None,
        ams_application_id: None,
        swap_application_id: Some(swap_application_id),
        enable_mining: config.enable_mining,
        mining_supply: config.mining_supply,
        now: Timestamp::now(),
    };
    let _ = contract
        .execute_operation(MemeOperation::Initialize { argument })
        .now_or_never()
        .expect("Execution of meme operation should not await anything");

    (contract, state_app_state)
}

fn dispatch_state_operation(
    state: &mut StateAppState,
    operation: &[u8],
) -> Vec<u8> {
    let operation = bcs::from_bytes::<MemeStateV1Operation>(operation)
        .expect("Failed to deserialize state app operation");
    let response = match operation {
        MemeStateV1Operation::Initialize { argument } => {
            state.initialize(argument).blocking_wait().map(|_| MemeStateV1Response::Ok)
        }
        MemeStateV1Operation::Transfer { from, to, amount } => state
            .transfer(from, to, amount)
            .blocking_wait()
            .map(|_| MemeStateV1Response::Ok),
        MemeStateV1Operation::TransferFrom {
            origin,
            from,
            to,
            amount,
        } => state
            .transfer_from(origin, from, to, amount)
            .blocking_wait()
            .map(|_| MemeStateV1Response::Ok),
        MemeStateV1Operation::TransferFromApplication { from, to, amount } => state
            .transfer(from, to, amount)
            .blocking_wait()
            .map(|_| MemeStateV1Response::Ok),
        MemeStateV1Operation::Approve {
            origin,
            spender,
            amount,
        } => state
            .approve(origin, spender, amount)
            .blocking_wait()
            .map(|_| MemeStateV1Response::Ok),
        MemeStateV1Operation::Mint { to, amount } => state
            .mint(to, amount)
            .blocking_wait()
            .map(|_| MemeStateV1Response::Ok),
        MemeStateV1Operation::TransferOwnership { owner, new_owner } => state
            .transfer_ownership(owner, new_owner)
            .blocking_wait()
            .map(|_| MemeStateV1Response::Ok),
        MemeStateV1Operation::Redeem { from, to, amount } => {
            let amount = match amount {
                Some(amount) => amount,
                None => state.balance_of(from).blocking_wait().unwrap(),
            };
            state.transfer(from, to, amount).blocking_wait().map(|_| MemeStateV1Response::Ok)
        }
        MemeStateV1Operation::MiningReward {
            owner,
            reward_amount,
            mining_info,
        } => state
            .mining_reward(owner, reward_amount, mining_info)
            .blocking_wait()
            .map(|_| MemeStateV1Response::Ok),
        MemeStateV1Operation::MiningInfo => state
            .mining_info()
            .blocking_wait()
            .map(MemeStateV1Response::MiningInfo),
        MemeStateV1Operation::Handoff { argument } => state
            .handoff(argument)
            .blocking_wait()
            .map(|_| MemeStateV1Response::Ok),
        MemeStateV1Operation::Balance { owner } => state
            .balance_of(owner)
            .blocking_wait()
            .map(MemeStateV1Response::Balance),
        MemeStateV1Operation::Allowance { owner, spender } => state
            .allowance_of(owner, spender)
            .blocking_wait()
            .map(MemeStateV1Response::Allowance),
        MemeStateV1Operation::Owner => state.owner().blocking_wait().map(MemeStateV1Response::Owner),
        MemeStateV1Operation::SwapApplicationId => state
            .swap_application_id()
            .blocking_wait()
            .map(MemeStateV1Response::SwapApplicationId),
        MemeStateV1Operation::ProxyApplicationId => state
            .proxy_application_id()
            .blocking_wait()
            .map(MemeStateV1Response::ProxyApplicationId),
        MemeStateV1Operation::StartMining => state
            .start_mining()
            .blocking_wait()
            .map(|_| MemeStateV1Response::Ok),
    };
    match response {
        Ok(response) => bcs::to_bytes(&response).expect("Failed to serialize state response"),
        Err(error) => bcs::to_bytes(&MemeStateV1Response::Fail(format!("{}", error)))
            .expect("Failed to serialize state response"),
    }
}

fn mock_non_state_application_call(
    _authenticated: bool,
    _application_id: ApplicationId,
    operation: &[u8],
) -> Vec<u8> {
    if bcs::from_bytes::<PoolOperation>(operation).is_ok() {
        bcs::to_bytes(&PoolResponse::Ok).unwrap()
    } else {
        bcs::to_bytes(&abi::proxy::ProxyResponse::Ok).unwrap()
    }
}

async fn balance_of(state: &Rc<RefCell<StateAppState>>, owner: Account) -> Amount {
    let operation = MemeStateV1Operation::Balance { owner };
    let response_bytes = dispatch_state_operation(
        &mut state.borrow_mut(),
        &bcs::to_bytes(&operation).unwrap(),
    );
    match bcs::from_bytes::<MemeStateV1Response>(&response_bytes).unwrap() {
        MemeStateV1Response::Balance(amount) => amount,
        _ => panic!("Invalid state response"),
    }
}

async fn allowance_of(state: &Rc<RefCell<StateAppState>>, owner: Account, spender: Account) -> Amount {
    let operation = MemeStateV1Operation::Allowance { owner, spender };
    let response_bytes = dispatch_state_operation(
        &mut state.borrow_mut(),
        &bcs::to_bytes(&operation).unwrap(),
    );
    match bcs::from_bytes::<MemeStateV1Response>(&response_bytes).unwrap() {
        MemeStateV1Response::Allowance(amount) => amount,
        _ => panic!("Invalid state response"),
    }
}

async fn owner_of(state: &Rc<RefCell<StateAppState>>) -> Account {
    let operation = MemeStateV1Operation::Owner;
    let response_bytes = dispatch_state_operation(
        &mut state.borrow_mut(),
        &bcs::to_bytes(&operation).unwrap(),
    );
    match bcs::from_bytes::<MemeStateV1Response>(&response_bytes).unwrap() {
        MemeStateV1Response::Owner(owner) => owner,
        _ => panic!("Invalid state response"),
    }
}

async fn swap_application_id_of(state: &Rc<RefCell<StateAppState>>) -> Option<ApplicationId> {
    let operation = MemeStateV1Operation::SwapApplicationId;
    let response_bytes = dispatch_state_operation(
        &mut state.borrow_mut(),
        &bcs::to_bytes(&operation).unwrap(),
    );
    match bcs::from_bytes::<MemeStateV1Response>(&response_bytes).unwrap() {
        MemeStateV1Response::SwapApplicationId(application_id) => application_id,
        _ => panic!("Invalid state response"),
    }
}

fn initial_owner_balance(_meme: &MemeContract) -> Amount {
    Amount::from_tokens(100)
}

fn initial_liquidity() -> Liquidity {
    Liquidity {
        fungible_amount: Amount::from_tokens(11000000),
        native_amount: Amount::from_tokens(10),
    }
}

fn alternate_account(chain_id: ChainId) -> Account {
    Account {
        chain_id,
        owner: AccountOwner::from_str(
            "0x02e900512d2fca22897f80a2f6932ff454f2752ef7afad18729dd25e5b5b6e03",
        )
        .unwrap(),
    }
}

fn application_account(meme: &MemeContract) -> Account {
    let mut runtime = meme.runtime.borrow_mut();
    Account {
        chain_id: runtime.chain_id(),
        owner: AccountOwner::from(runtime.application_id().forget_abi()),
    }
}

fn pool_application_account(chain_id: ChainId) -> Account {
    Account {
        chain_id,
        owner: AccountOwner::from(
            ApplicationId::from_str(
                "b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bbd",
            )
            .unwrap(),
        ),
    }
}

fn pool_claim_receipt(result: Option<Result<(), String>>) -> TransferFromApplicationReceipt {
    TransferFromApplicationReceipt {
        purpose: TransferFromApplicationReceiptPurpose::PoolClaim,
        owner: Account {
            chain_id: ChainId::from_str(
                "aee928d4bf3880353b4a3cd9b6f88e6cc6e5ed050860abae439e7782e9b2dfe8",
            )
            .unwrap(),
            owner: AccountOwner::from_str(
                "0x02e900512d2fca22897f80a2f6932ff454f2752ef7afad18729dd25e5b5b6e03",
            )
            .unwrap(),
        },
        token: ApplicationId::from_str(
            "b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bad",
        )
        .unwrap(),
        amount: Amount::from_tokens(5),
        result,
        payload: None,
    }
}

fn pool_add_liquidity_receipt(
    result: Option<Result<(), String>>,
    fund_type: FundType,
) -> TransferFromApplicationReceipt {
    let base = pool_claim_receipt(result);
    let request = FundRequest::builder(base.owner, Some(base.token), base.amount, fund_type)
        .counterparty_token(None)
        .counterparty_amount_in(Some(Amount::from_tokens(10)))
        .counterparty_amount_out_min(Some(Amount::ONE))
        .build();

    TransferFromApplicationReceipt {
        purpose: TransferFromApplicationReceiptPurpose::PoolAddLiquidity,
        payload: Some(TransferFromApplicationReceiptPayload::PoolAddLiquidity(
            AddLiquidityTransferReceiptPayload {
                prev: None,
                request,
                next: None,
            },
        )),
        ..base
    }
}

fn pool_swap_receipt(
    result: Option<Result<(), String>>,
    fund_type: FundType,
) -> TransferFromApplicationReceipt {
    let base = pool_claim_receipt(result);
    let request = FundRequest::builder(base.owner, Some(base.token), base.amount, fund_type)
        .counterparty_token(None)
        .counterparty_amount_out_min(Some(Amount::ONE))
        .build();

    TransferFromApplicationReceipt {
        purpose: TransferFromApplicationReceiptPurpose::PoolSwap,
        payload: Some(TransferFromApplicationReceiptPayload::PoolSwap(
            SwapTransferReceiptPayload { request },
        )),
        ..base
    }
}

fn assert_transfer_from_application_receipt(
    meme: &MemeContract,
    caller: Account,
    result: Result<(), String>,
) {
    let runtime = meme.runtime.borrow();
    let requests = runtime.created_send_message_requests();
    let request = requests.last().unwrap();
    assert_eq!(request.destination, caller.chain_id);
    assert!(request.authenticated);
    assert!(!request.is_tracked);
    assert!(matches!(
        &request.message,
        MemeMessage::TransferFromApplicationReceipt {
            caller: receipt_caller,
            receipt,
        } if *receipt_caller == caller
            && receipt.result == Some(result)
    ));
}

fn assert_transfer_from_application_receipt_err(meme: &MemeContract, caller: Account) {
    let runtime = meme.runtime.borrow();
    let requests = runtime.created_send_message_requests();
    let request = requests.last().unwrap();
    assert_eq!(request.destination, caller.chain_id);
    assert!(request.authenticated);
    assert!(!request.is_tracked);
    assert!(matches!(
        &request.message,
        MemeMessage::TransferFromApplicationReceipt {
            caller: receipt_caller,
            receipt,
        } if *receipt_caller == caller
            && matches!(receipt.result, Some(Err(_)))
    ));
}


