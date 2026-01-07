use super::super::{MemeContract, MemeState};

use meme::interfaces::state::StateInterface;

use abi::{
    meme::{
        InstantiationArgument, Liquidity, Meme, MemeAbi, MemeMessage, MemeOperation,
        MemeParameters, MemeResponse, Metadata,
    },
    store_type::StoreType,
    swap::router::SwapResponse,
};
use futures::FutureExt as _;
use linera_sdk::{
    bcs,
    linera_base_types::{
        Account, AccountOwner, Amount, ApplicationId, ChainId, ChainOwnership, CryptoHash,
        TestString, Timestamp,
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
#[should_panic(expected = "Not implemented")]
async fn operation_mine() {
    let mut meme = create_and_instantiate_meme().await;

    let _ = meme
        .execute_operation(MemeOperation::Mine {
            nonce: CryptoHash::new(&TestString::new("aaaa")),
        })
        .now_or_never()
        .expect("Execution of meme operation should not await anything");
}

#[tokio::test(flavor = "multi_thread")]
async fn user_chain_operation() {
    let mut meme = create_and_instantiate_meme().await;
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
    let mut meme = create_and_instantiate_meme().await;
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
    let mut meme = create_and_instantiate_meme().await;
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
    let mut meme = create_and_instantiate_meme().await;
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
    let mut meme = create_and_instantiate_meme().await;
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
    let mut meme = create_and_instantiate_meme().await;
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
    let mut meme = create_and_instantiate_meme().await;
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
    _operation: Vec<u8>,
) -> Vec<u8> {
    bcs::to_bytes(&SwapResponse::ChainId(
        ChainId::from_str("aee928d4bf3880353b4a3cd9b6f88e6cc6e5ed050860abae439e7782e9b2dfe8")
            .unwrap(),
    ))
    .unwrap()
}

async fn create_and_instantiate_meme() -> MemeContract {
    let operator = AccountOwner::from_str(
        "0x5279b3ae14d3b38e14b65a74aefe44824ea88b25c7841836e9ec77d991a5bc7f",
    )
    .unwrap();
    let chain_id =
        ChainId::from_str("aee928d4bf3880353b4a3cd9b6f88e6cc6e5ed050860abae439e7782e9b2dfe8")
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
    let swap_allowance = Amount::from_tokens(10000000);
    let parameters = MemeParameters {
        creator: owner,
        initial_liquidity: Some(Liquidity {
            fungible_amount: swap_allowance,
            native_amount: Amount::from_tokens(10),
        }),
        virtual_initial_liquidity: true,
        swap_creator_chain_id: chain_id,

        enable_mining: false,
        mining_supply: None,
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
        proxy_application_id: None,
        swap_application_id: Some(swap_application_id),
    };

    contract.instantiate(instantiation_argument.clone()).await;
    let application_balance = initial_supply
        .try_sub(swap_allowance)
        .unwrap()
        .try_sub(contract.state.borrow().initial_owner_balance())
        .unwrap();

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

    contract
}
