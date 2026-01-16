use super::super::{MemeContract, MemeState};

use meme::interfaces::state::StateInterface;

use abi::{
    meme::{
        InstantiationArgument, Liquidity, Meme, MemeAbi, MemeMessage, MemeOperation,
        MemeParameters, MemeResponse, Metadata,
    },
    proxy::{Miner, ProxyOperation, ProxyResponse},
    store_type::StoreType,
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
use runtime::{
    contract::ContractRuntimeAdapter,
    interfaces::{base::BaseRuntimeContext, contract::ContractRuntimeContext},
};
use std::str::FromStr;
use std::{cell::RefCell, rc::Rc};

#[tokio::test(flavor = "multi_thread")]
#[should_panic(expected = "Not enabled")]
async fn operation_mine_not_enable_mining() {
    let mut meme = create_and_instantiate_meme(false, None).await;

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
    let mut meme = create_and_instantiate_meme(true, None).await;

    let _ = meme
        .execute_operation(MemeOperation::Mine {
            nonce: CryptoHash::new(&TestString::new("aaaa")),
        })
        .now_or_never()
        .expect("Execution of meme operation should not await anything");
}

#[tokio::test(flavor = "multi_thread")]
async fn operation_mine_enable_mining_supply_none_one_block() {
    let mut meme = create_and_instantiate_meme(true, None).await;

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
    let mut meme = create_and_instantiate_meme(true, None).await;

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
    let mut meme = create_and_instantiate_meme(true, Some(Amount::from_tokens(10000000))).await;

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
    let mut meme = create_and_instantiate_meme(true, Some(Amount::from_tokens(13000000))).await;

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
    let mut meme = create_and_instantiate_meme(false, None).await;
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
async fn message_transfer() {
    let mut meme = create_and_instantiate_meme(false, None).await;
    let mut runtime_context = ContractRuntimeAdapter::new(meme.runtime.clone());

    let from = runtime_context.authenticated_account();
    let amount = meme.state.borrow().initial_owner_balance();

    let to = Account {
        chain_id: runtime_context.chain_id(),
        owner: AccountOwner::from_str(
            "0x5279b3ae14d3b38e14b65a74aefe44824ea88b25c7841836e9ec77d991a5bc8f",
        )
        .unwrap(),
    };

    assert_eq!(
        meme.state
            .borrow()
            .balances
            .contains_key(&from)
            .await
            .unwrap(),
        true
    );
    let balance = meme
        .state
        .borrow()
        .balances
        .get(&from)
        .await
        .unwrap()
        .unwrap();
    assert_eq!(balance, amount);

    meme.execute_message(MemeMessage::Transfer { from, to, amount })
        .await;

    assert_eq!(
        meme.state
            .borrow()
            .balances
            .contains_key(&to)
            .await
            .unwrap(),
        true
    );
    let balance = meme
        .state
        .borrow()
        .balances
        .get(&to)
        .await
        .unwrap()
        .unwrap();
    assert_eq!(balance, amount);
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic(expected = "Insufficient balance")]
async fn message_transfer_insufficient_funds() {
    let mut meme = create_and_instantiate_meme(false, None).await;
    let mut runtime_context = ContractRuntimeAdapter::new(meme.runtime.clone());

    let from = runtime_context.authenticated_account();
    let amount = meme.state.borrow().initial_owner_balance();
    let transfer_amount = amount.try_add(Amount::ONE).unwrap();

    let to = Account {
        chain_id: runtime_context.chain_id(),
        owner: AccountOwner::from_str(
            "0x5279b3ae14d3b38e14b65a74aefe44824ea88b25c7841836e9ec77d991a5bc8f",
        )
        .unwrap(),
    };

    assert_eq!(
        meme.state
            .borrow()
            .balances
            .contains_key(&from)
            .await
            .unwrap(),
        true
    );
    let balance = meme
        .state
        .borrow()
        .balances
        .get(&from)
        .await
        .unwrap()
        .unwrap();
    assert_eq!(balance, amount);

    meme.execute_message(MemeMessage::Transfer {
        from,
        to,
        amount: transfer_amount,
    })
    .await;

    assert_eq!(
        meme.state
            .borrow()
            .balances
            .contains_key(&to)
            .await
            .unwrap(),
        true
    );
    let balance = meme
        .state
        .borrow()
        .balances
        .get(&to)
        .await
        .unwrap()
        .unwrap();
    assert_eq!(balance, amount);
}

#[tokio::test(flavor = "multi_thread")]
async fn message_approve_owner_success() {
    let mut meme = create_and_instantiate_meme(false, None).await;
    let mut runtime_context = ContractRuntimeAdapter::new(meme.runtime.clone());

    let from = runtime_context.authenticated_account();

    let amount = meme.state.borrow().initial_owner_balance();
    let allowance = Amount::from_tokens(22);

    let spender = Account {
        chain_id: runtime_context.chain_id(),
        owner: AccountOwner::from_str(
            "0x5279b3ae14d3b38e14b65a74aefe44824ea88b25c7841836e9ec77d991a5bc8f",
        )
        .unwrap(),
    };

    assert_eq!(
        meme.state
            .borrow()
            .balances
            .contains_key(&from)
            .await
            .unwrap(),
        true
    );
    let balance = meme
        .state
        .borrow()
        .balances
        .get(&from)
        .await
        .unwrap()
        .unwrap();
    assert_eq!(balance, amount);

    meme.execute_message(MemeMessage::Approve {
        owner: from,
        spender,
        amount: allowance,
    })
    .await;

    let balance = meme
        .state
        .borrow()
        .balances
        .get(&from)
        .await
        .unwrap()
        .unwrap();
    assert_eq!(balance, amount.try_sub(allowance).unwrap());

    assert_eq!(
        meme.state
            .borrow()
            .allowances
            .contains_key(&from)
            .await
            .unwrap(),
        true
    );
    assert_eq!(
        meme.state
            .borrow()
            .allowances
            .get(&from)
            .await
            .unwrap()
            .unwrap()
            .contains_key(&spender),
        true
    );
    let balance = *meme
        .state
        .borrow()
        .allowances
        .get(&from)
        .await
        .unwrap()
        .unwrap()
        .get(&spender)
        .unwrap();
    assert_eq!(balance, allowance);

    meme.execute_message(MemeMessage::Approve {
        owner: from,
        spender,
        amount: allowance,
    })
    .await;

    let balance = meme
        .state
        .borrow()
        .balances
        .get(&from)
        .await
        .unwrap()
        .unwrap();
    assert_eq!(
        balance,
        amount
            .try_sub(allowance)
            .unwrap()
            .try_sub(allowance)
            .unwrap()
    );

    let balance = *meme
        .state
        .borrow()
        .allowances
        .get(&from)
        .await
        .unwrap()
        .unwrap()
        .get(&spender)
        .unwrap();
    assert_eq!(balance, allowance.try_mul(2).unwrap());

    let to = Account {
        chain_id: meme.runtime.borrow_mut().chain_id(),
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

    let balance = *meme
        .state
        .borrow()
        .allowances
        .get(&from)
        .await
        .unwrap()
        .unwrap()
        .get(&spender)
        .unwrap();
    assert_eq!(balance, allowance);

    let balance = meme
        .state
        .borrow()
        .balances
        .get(&to)
        .await
        .unwrap()
        .unwrap();
    assert_eq!(balance, allowance);
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic(expected = "Insufficient balance")]
async fn message_approve_insufficient_balance() {
    let mut meme = create_and_instantiate_meme(false, None).await;
    let mut runtime_context = ContractRuntimeAdapter::new(meme.runtime.clone());

    let from = runtime_context.authenticated_account();

    let amount = meme.state.borrow().initial_owner_balance();
    let allowance = Amount::from_tokens(220);

    let spender = Account {
        chain_id: runtime_context.chain_id(),
        owner: AccountOwner::from_str(
            "0x5279b3ae14d3b38e14b65a74aefe44824ea88b25c7841836e9ec77d991a5bc8f",
        )
        .unwrap(),
    };

    assert_eq!(
        meme.state
            .borrow()
            .balances
            .contains_key(&from)
            .await
            .unwrap(),
        true
    );
    let balance = meme
        .state
        .borrow()
        .balances
        .get(&from)
        .await
        .unwrap()
        .unwrap();
    assert_eq!(balance, amount);

    // It won't panic here, it'll approved from application balance
    meme.execute_message(MemeMessage::Approve {
        owner: from,
        spender,
        amount: allowance,
    })
    .await;

    let balance = meme
        .state
        .borrow()
        .balances
        .get(&from)
        .await
        .unwrap()
        .unwrap();
    assert_eq!(balance, amount);

    assert_eq!(
        meme.state
            .borrow()
            .allowances
            .contains_key(&from)
            .await
            .unwrap(),
        false
    );
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic(expected = "Insufficient balance")]
async fn message_approve_meme_owner_self_insufficient_balance() {
    let mut meme = create_and_instantiate_meme(false, None).await;
    let mut runtime_context = ContractRuntimeAdapter::new(meme.runtime.clone());

    let from = runtime_context.authenticated_account();

    let amount = meme.state.borrow().initial_owner_balance();
    let allowance = Amount::from_tokens(220);

    assert_eq!(
        meme.state
            .borrow()
            .balances
            .contains_key(&from)
            .await
            .unwrap(),
        true
    );
    let balance = meme
        .state
        .borrow()
        .balances
        .get(&from)
        .await
        .unwrap()
        .unwrap();
    assert_eq!(balance, amount);

    // It won't panic here, it'll approved from application balance
    meme.execute_message(MemeMessage::Approve {
        owner: from,
        spender: from,
        amount: allowance,
    })
    .await;

    assert_eq!(
        meme.state
            .borrow()
            .allowances
            .contains_key(&from)
            .await
            .unwrap(),
        false
    );
}

#[tokio::test(flavor = "multi_thread")]
async fn message_transfer_ownership() {
    let mut meme = create_and_instantiate_meme(false, None).await;
    let mut runtime_context = ContractRuntimeAdapter::new(meme.runtime.clone());

    let owner = runtime_context.authenticated_account();
    let new_owner = Account {
        chain_id: meme.runtime.borrow_mut().chain_id(),
        owner: AccountOwner::from_str(
            "0x5279b3ae14d3b38e14b65a74aefe44824ea88b25c7841836e9ec77d991a5bc8f",
        )
        .unwrap(),
    };

    // It won't panic here, it'll approved from application balance
    meme.execute_message(MemeMessage::TransferOwnership { owner, new_owner })
        .await;

    assert_eq!(meme.state.borrow().owner.get().unwrap(), new_owner);
}

#[test]
fn cross_application_call() {}

fn mock_application_call(
    _authenticated: bool,
    _application_id: ApplicationId,
    operation: Vec<u8>,
) -> Vec<u8> {
    if let Ok(op) = bcs::from_bytes::<ProxyOperation>(&operation) {
        match op {
            ProxyOperation::GetMinerWithAuthenticatedSigner => {
                return bcs::to_bytes(&ProxyResponse::Miner(Miner {
                    owner: Account {
                        chain_id: ChainId::from_str(
                            "abdb7c1079f36eaa03f629540283a881eb4256d1ece83a84415022d4d2a9ac65",
                        )
                        .unwrap(),
                        owner: AccountOwner::from_str(
                            "0xfd90bbb496d286ff1227b8aa2f0d8e479d2b425257940bf36c4338ab73705ac6",
                        )
                        .unwrap(),
                    },
                    registered_at: 0.into(),
                }))
                .unwrap();
            }
            _ => return bcs::to_bytes(&ProxyResponse::Ok).unwrap(),
        }
    }

    bcs::to_bytes(&ProxyResponse::Ok).unwrap()
}

async fn create_and_instantiate_meme(
    enable_mining: bool,
    mining_supply: Option<Amount>,
) -> MemeContract {
    let operator = AccountOwner::from_str(
        "0xfd90bbb496d286ff1227b8aa2f0d8e479d2b425257940bf36c4338ab73705ac6",
    )
    .unwrap();
    let chain_id =
        ChainId::from_str("abdb7c1079f36eaa03f629540283a881eb4256d1ece83a84415022d4d2a9ac65")
            .unwrap();
    let owner = Account {
        chain_id,
        owner: operator,
    };

    let application_id =
        ApplicationId::from_str("b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bad")
            .unwrap()
            .with_abi::<MemeAbi>();
    let application = Account {
        chain_id,
        owner: AccountOwner::from(application_id.forget_abi()),
    };

    let swap_application_id =
        ApplicationId::from_str("b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bae")
            .unwrap();
    let swap_application = Account {
        chain_id,
        owner: AccountOwner::from(swap_application_id),
    };

    let initial_supply = Amount::from_tokens(21000000);
    let mut swap_allowance = Amount::from_tokens(10000000);
    let parameters = MemeParameters {
        creator: owner,
        initial_liquidity: Some(Liquidity {
            fungible_amount: swap_allowance,
            native_amount: Amount::from_tokens(10),
        }),
        virtual_initial_liquidity: true,
        swap_creator_chain_id: chain_id,

        enable_mining,
        mining_supply,
    };
    let runtime = ContractRuntime::new()
        .with_can_change_application_permissions(true)
        .with_chain_id(chain_id)
        .with_application_id(application_id)
        .with_chain_ownership(ChainOwnership::single(operator))
        .with_owner_balance(
            AccountOwner::from(application_id.forget_abi()),
            Amount::from_tokens(10000),
        )
        .with_owner_balance(operator, Amount::from_tokens(10000))
        .with_owner_balance(AccountOwner::from(swap_application_id), Amount::ZERO)
        .with_chain_balance(Amount::ONE)
        .with_authenticated_caller_id(swap_application_id)
        .with_call_application_handler(mock_application_call)
        .with_application_creator_chain_id(chain_id)
        .with_application_parameters(parameters.clone())
        .with_system_time(Timestamp::now())
        .with_block_height(BlockHeight(0))
        .with_authenticated_signer(operator);
    let mut contract = MemeContract {
        state: Rc::new(RefCell::new(
            MemeState::load(runtime.root_view_storage_context())
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
        proxy_application_id: Some(
            ApplicationId::from_str(
                "abdb7c1079f36eaa03f629540283a881eb4256d1ece83a84415022d4d2a9ac65",
            )
            .unwrap(),
        ),
        swap_application_id: Some(swap_application_id),
    };

    contract.instantiate(instantiation_argument.clone()).await;
    let mut application_balance = if enable_mining && mining_supply.is_none() {
        initial_supply
            .try_sub(contract.state.borrow().initial_owner_balance())
            .unwrap()
    } else {
        initial_supply
            .try_sub(swap_allowance)
            .unwrap()
            .try_sub(contract.state.borrow().initial_owner_balance())
            .unwrap()
    };
    let mining_supply = if enable_mining {
        mining_supply.unwrap_or(
            initial_supply
                .try_sub(contract.state.borrow().initial_owner_balance())
                .unwrap(),
        )
    } else {
        Amount::ZERO
    };

    if mining_supply
        .try_add(swap_allowance)
        .unwrap()
        .try_add(contract.state.borrow().initial_owner_balance())
        .unwrap()
        > initial_supply
    {
        swap_allowance = initial_supply
            .try_sub(mining_supply)
            .unwrap()
            .try_sub(contract.state.borrow().initial_owner_balance())
            .unwrap();
        application_balance = mining_supply;
    }

    assert_eq!(
        *contract.state.borrow().meme.get().as_ref().unwrap(),
        instantiation_argument.meme
    );
    assert_eq!(
        contract
            .state
            .borrow()
            .balances
            .contains_key(&application)
            .await
            .unwrap(),
        true
    );
    assert_eq!(
        contract
            .state
            .borrow()
            .balances
            .get(&application)
            .await
            .as_ref()
            .unwrap()
            .unwrap(),
        application_balance,
    );
    // If mining_supply is none, we don't need create liquidity pool
    // TODO: process mining_supply + swap_allowance > balance
    if swap_allowance > Amount::ZERO {
        assert_eq!(
            contract
                .state
                .borrow()
                .allowances
                .contains_key(&application)
                .await
                .unwrap(),
            true
        );
        assert_eq!(
            contract
                .state
                .borrow()
                .allowances
                .get(&application)
                .await
                .unwrap()
                .unwrap()
                .contains_key(&swap_application),
            true
        );
        assert_eq!(
            *contract
                .state
                .borrow()
                .allowances
                .get(&application)
                .await
                .unwrap()
                .unwrap()
                .get(&swap_application)
                .unwrap(),
            swap_allowance
        );
    }

    contract
}
