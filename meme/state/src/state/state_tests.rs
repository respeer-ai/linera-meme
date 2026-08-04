use crate::{
    interfaces::state::StateInterface,
    state::{errors::StateError, MemeState},
};

use abi::meme::{
    HandoffArgument, InitializeArgument, Liquidity, Meme, Metadata, StateInstantiationArgument,
};
use linera_sdk::{
    linera_base_types::{
        Account, AccountOwner, Amount, ApplicationId, BlockHeight, ChainId, CryptoHash, TestString,
        Timestamp,
    },
    util::BlockingWait,
    views::{KeyValueStore, View, ViewStorageContext},
};
use std::str::FromStr;

fn test_chain_id() -> ChainId {
    ChainId::from_str("abdb7c1079f36eaa03f629540283a881eb4256d1ece83a84415022d4d2a9ac65")
        .unwrap()
}

fn test_operator() -> AccountOwner {
    AccountOwner::from_str(
        "0xfd90bbb496d286ff1227b8aa2f0d8e479d2b425257940bf36c4338ab73705ac6",
    )
    .unwrap()
}

fn test_business_application_id() -> ApplicationId {
    ApplicationId::from_str(
        "b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bad",
    )
    .unwrap()
}

fn test_swap_application_id() -> ApplicationId {
    ApplicationId::from_str(
        "b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bae",
    )
    .unwrap()
}

fn test_account(owner: AccountOwner) -> Account {
    Account {
        chain_id: test_chain_id(),
        owner,
    }
}

fn test_owner() -> Account {
    test_account(test_operator())
}

fn test_holder() -> Account {
    test_account(AccountOwner::from(test_business_application_id()))
}

fn test_meme() -> Meme {
    Meme {
        name: "Test Token".to_string(),
        ticker: "LTT".to_string(),
        decimals: 6,
        initial_supply: Amount::from_tokens(21000000),
        total_supply: Amount::from_tokens(21000000),
        metadata: Metadata {
            logo_store_type: abi::store_type::StoreType::S3,
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
        initial_liquidity: Some(Liquidity {
            fungible_amount: Amount::from_tokens(11000000),
            native_amount: Amount::from_tokens(10),
        }),
    }
}

fn create_state() -> MemeState {
    let store = KeyValueStore::mock().to_mut();
    let context = ViewStorageContext::new_unchecked(store, Vec::new(), ());
    MemeState::load(context)
        .blocking_wait()
        .expect("Failed to load meme state")
}

fn instantiate_state() -> MemeState {
    let mut state = create_state();
    state.instantiate(StateInstantiationArgument {
        business_application_id: test_business_application_id(),
        operator: Some(test_owner()),
        proxy_application_id: Some(test_business_application_id()),
    });
    state
}

fn initialize_state() -> MemeState {
    initialize_state_with_mining(false, None)
}

fn initialize_state_with_mining(
    enable_mining: bool,
    mining_supply: Option<Amount>,
) -> MemeState {
    let mut state = instantiate_state();
    let meme = test_meme();
    let initial_owner_balance = Amount::from_tokens(100);
    state
        .initialize(InitializeArgument {
            owner: test_owner(),
            holder: test_holder(),
            meme,
            initial_owner_balance,
            blob_gateway_application_id: None,
            ams_application_id: None,
            swap_application_id: Some(test_swap_application_id()),
            enable_mining,
            mining_supply,
            now: Timestamp::now(),
        })
        .blocking_wait()
        .expect("Failed to initialize state");
    state
}

#[tokio::test(flavor = "multi_thread")]
async fn instantiate_sets_metadata() {
    let mut state = instantiate_state();

    assert_eq!(
        state.business_application_id().await.unwrap(),
        test_business_application_id()
    );
    assert_eq!(state.operator().await.unwrap(), test_owner());
    assert_eq!(
        state.proxy_application_id().await.unwrap(),
        Some(test_business_application_id())
    );
}

#[tokio::test(flavor = "multi_thread")]
async fn initialize_sets_owner_holder_and_balances() {
    let state = initialize_state();

    assert_eq!(state.owner().await.unwrap(), test_owner());
    assert_eq!(state.holder.get().unwrap(), test_holder());
    assert_eq!(
        state.balance_of(test_holder()).await.unwrap(),
        test_meme().initial_supply
    );
}

#[tokio::test(flavor = "multi_thread")]
async fn initialize_twice_fails() {
    let mut state = initialize_state();
    let meme = test_meme();
    let err = state
        .initialize(InitializeArgument {
            owner: test_owner(),
            holder: test_holder(),
            meme,
            initial_owner_balance: Amount::from_tokens(100),
            blob_gateway_application_id: None,
            ams_application_id: None,
            swap_application_id: Some(test_swap_application_id()),
            enable_mining: false,
            mining_supply: None,
            now: Timestamp::now(),
        })
        .await
        .unwrap_err();
    assert!(matches!(err, StateError::AlreadyInitialized));
}

#[tokio::test(flavor = "multi_thread")]
async fn transfer_moves_balance() {
    let mut state = initialize_state();
    let recipient = test_account(AccountOwner::from_str(
        "0x5279b3ae14d3b38e14b65a74aefe44824ea88b25c7841836e9ec77d991a5bc8f",
    ).unwrap());
    let amount = Amount::from_tokens(100);

    state
        .transfer(test_holder(), recipient, amount)
        .await
        .unwrap();

    assert_eq!(
        state.balance_of(test_holder()).await.unwrap(),
        test_meme().initial_supply.saturating_sub(amount)
    );
    assert_eq!(state.balance_of(recipient).await.unwrap(), amount);
}

#[tokio::test(flavor = "multi_thread")]
async fn transfer_zero_fails() {
    let mut state = initialize_state();
    let recipient = test_account(AccountOwner::from_str(
        "0x5279b3ae14d3b38e14b65a74aefe44824ea88b25c7841836e9ec77d991a5bc8f",
    ).unwrap());

    let err = state
        .transfer(test_holder(), recipient, Amount::ZERO)
        .await
        .unwrap_err();
    assert!(matches!(err, StateError::InvalidAmount));
}

#[tokio::test(flavor = "multi_thread")]
async fn transfer_self_fails() {
    let mut state = initialize_state();

    let err = state
        .transfer(test_holder(), test_holder(), Amount::ONE)
        .await
        .unwrap_err();
    assert!(matches!(err, StateError::SelfTransfer));
}

#[tokio::test(flavor = "multi_thread")]
async fn transfer_insufficient_funds_fails() {
    let mut state = initialize_state();
    let recipient = test_account(AccountOwner::from_str(
        "0x5279b3ae14d3b38e14b65a74aefe44824ea88b25c7841836e9ec77d991a5bc8f",
    ).unwrap());

    let err = state
        .transfer(
            test_holder(),
            recipient,
            test_meme().initial_supply.try_add(Amount::ONE).unwrap(),
        )
        .await
        .unwrap_err();
    assert!(matches!(err, StateError::InsufficientFunds));
}

#[tokio::test(flavor = "multi_thread")]
async fn approve_reserves_balance_and_allowance() {
    let mut state = initialize_state();
    let spender = test_account(AccountOwner::from_str(
        "0x5279b3ae14d3b38e14b65a74aefe44824ea88b25c7841836e9ec77d991a5bc8f",
    ).unwrap());
    let allowance = Amount::from_tokens(100);

    state
        .approve(test_holder(), spender, allowance)
        .await
        .unwrap();

    assert_eq!(
        state.balance_of(test_holder()).await.unwrap(),
        test_meme().initial_supply.saturating_sub(allowance)
    );
    assert_eq!(
        state.allowance_of(test_holder(), spender).await.unwrap(),
        allowance
    );
}

#[tokio::test(flavor = "multi_thread")]
async fn approve_insufficient_funds_fails() {
    let mut state = initialize_state();
    let spender = test_account(AccountOwner::from_str(
        "0x5279b3ae14d3b38e14b65a74aefe44824ea88b25c7841836e9ec77d991a5bc8f",
    ).unwrap());

    let err = state
        .approve(
            test_holder(),
            spender,
            test_meme().initial_supply.try_add(Amount::ONE).unwrap(),
        )
        .await
        .unwrap_err();
    assert!(matches!(err, StateError::InsufficientFunds));
}

#[tokio::test(flavor = "multi_thread")]
async fn approve_self_fails() {
    let mut state = initialize_state();

    let err = state
        .approve(test_holder(), test_holder(), Amount::ONE)
        .await
        .unwrap_err();
    assert!(matches!(err, StateError::InvalidOwner));
}

#[tokio::test(flavor = "multi_thread")]
async fn transfer_from_uses_allowance() {
    let mut state = initialize_state();
    let spender = test_account(AccountOwner::from_str(
        "0x5279b3ae14d3b38e14b65a74aefe44824ea88b25c7841836e9ec77d991a5bc8f",
    ).unwrap());
    let recipient = test_account(AccountOwner::from_str(
        "0x02e900512d2fca22897f80a2f6932ff454f2752ef7afad18729dd25e5b5b6e08",
    ).unwrap());

    state
        .approve(test_holder(), spender, Amount::from_tokens(100))
        .await
        .unwrap();
    state
        .transfer_from(spender, test_holder(), recipient, Amount::from_tokens(30))
        .await
        .unwrap();

    assert_eq!(
        state.allowance_of(test_holder(), spender).await.unwrap(),
        Amount::from_tokens(70)
    );
    assert_eq!(
        state.balance_of(recipient).await.unwrap(),
        Amount::from_tokens(30)
    );
}

#[tokio::test(flavor = "multi_thread")]
async fn transfer_from_insufficient_allowance_fails() {
    let mut state = initialize_state();
    let spender = test_account(AccountOwner::from_str(
        "0x5279b3ae14d3b38e14b65a74aefe44824ea88b25c7841836e9ec77d991a5bc8f",
    ).unwrap());
    let recipient = test_account(AccountOwner::from_str(
        "0x02e900512d2fca22897f80a2f6932ff454f2752ef7afad18729dd25e5b5b6e08",
    ).unwrap());

    let err = state
        .transfer_from(spender, test_holder(), recipient, Amount::ONE)
        .await
        .unwrap_err();
    assert!(matches!(err, StateError::InsufficientAllowance));
}

#[tokio::test(flavor = "multi_thread")]
async fn mint_transfers_from_holder() {
    let mut state = initialize_state();
    let recipient = test_account(AccountOwner::from_str(
        "0x5279b3ae14d3b38e14b65a74aefe44824ea88b25c7841836e9ec77d991a5bc8f",
    ).unwrap());
    let amount = Amount::from_tokens(100);

    state.mint(recipient, amount).await.unwrap();

    assert_eq!(state.balance_of(recipient).await.unwrap(), amount);
    assert_eq!(
        state.balance_of(test_holder()).await.unwrap(),
        test_meme().initial_supply.saturating_sub(amount)
    );
}

#[tokio::test(flavor = "multi_thread")]
async fn transfer_ownership_changes_owner() {
    let mut state = initialize_state();
    let new_owner = test_account(AccountOwner::from_str(
        "0x5279b3ae14d3b38e14b65a74aefe44824ea88b25c7841836e9ec77d991a5bc8f",
    ).unwrap());

    state
        .transfer_ownership(test_owner(), new_owner)
        .await
        .unwrap();

    assert_eq!(state.owner().await.unwrap(), new_owner);
}

#[tokio::test(flavor = "multi_thread")]
async fn transfer_ownership_wrong_owner_fails() {
    let mut state = initialize_state();
    let fake_owner = test_account(AccountOwner::from_str(
        "0x5279b3ae14d3b38e14b65a74aefe44824ea88b25c7841836e9ec77d991a5bc8f",
    ).unwrap());
    let new_owner = test_account(AccountOwner::from_str(
        "0x02e900512d2fca22897f80a2f6932ff454f2752ef7afad18729dd25e5b5b6e08",
    ).unwrap());

    let err = state
        .transfer_ownership(fake_owner, new_owner)
        .await
        .unwrap_err();
    assert!(matches!(err, StateError::InvalidOwner));
}

#[tokio::test(flavor = "multi_thread")]
async fn initialize_liquidity_reserves_allowance() {
    let mut state = initialize_state();
    let liquidity = Liquidity {
        fungible_amount: Amount::from_tokens(1000),
        native_amount: Amount::from_tokens(10),
    };

    state
        .initialize_liquidity(liquidity.clone(), test_chain_id(), false, None)
        .await
        .unwrap();

    let swap_spender = Account {
        chain_id: test_chain_id(),
        owner: AccountOwner::from(test_swap_application_id()),
    };
    assert_eq!(
        state.allowance_of(test_holder(), swap_spender).await.unwrap(),
        liquidity.fungible_amount
    );
    assert_eq!(state.initial_liquidity.get().clone().unwrap(), liquidity);
}

#[tokio::test(flavor = "multi_thread")]
async fn mining_reward_mints_and_updates_mining_info() {
    let mut state = initialize_state_with_mining(true, None);
    let mut mining_info = state.mining_info().await.unwrap();
    let reward = mining_info.reward_amount;
    let recipient = test_account(AccountOwner::from_str(
        "0x5279b3ae14d3b38e14b65a74aefe44824ea88b25c7841836e9ec77d991a5bc8f",
    ).unwrap());

    mining_info.mining_height = BlockHeight(1);
    state
        .mining_reward(recipient, reward, mining_info)
        .await
        .unwrap();

    assert_eq!(state.balance_of(recipient).await.unwrap(), reward);
    assert_eq!(
        state.mining_info().await.unwrap().mining_height,
        BlockHeight(1)
    );
}

#[tokio::test(flavor = "multi_thread")]
async fn start_mining_sets_started_flag() {
    let mut state = initialize_state_with_mining(true, None);

    assert!(!state.mining_info().await.unwrap().mining_started);
    state.start_mining().await.unwrap();
    assert!(state.mining_info().await.unwrap().mining_started);
}

#[tokio::test(flavor = "multi_thread")]
async fn handoff_updates_ids() {
    let mut state = initialize_state();
    let new_business = ApplicationId::from_str(
        "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    )
    .unwrap();
    let new_proxy = ApplicationId::from_str(
        "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    )
    .unwrap();
    let new_swap = ApplicationId::from_str(
        "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
    )
    .unwrap();

    state
        .handoff(HandoffArgument {
            new_business_application_id: new_business,
            new_proxy_application_id: Some(new_proxy),
            new_swap_application_id: Some(new_swap),
            new_ams_application_id: None,
            new_blob_gateway_application_id: None,
        })
        .await
        .unwrap();

    assert_eq!(
        state.business_application_id().await.unwrap(),
        new_business
    );
    assert_eq!(
        state.proxy_application_id().await.unwrap(),
        Some(new_proxy)
    );
    assert_eq!(state.swap_application_id().await.unwrap(), Some(new_swap));
}

#[tokio::test(flavor = "multi_thread")]
async fn default_balances_and_allowances_are_zero() {
    let state = initialize_state();
    let account = test_account(AccountOwner::from_str(
        "0x5279b3ae14d3b38e14b65a74aefe44824ea88b25c7841836e9ec77d991a5bc8f",
    ).unwrap());

    assert_eq!(state.balance_of(account).await.unwrap(), Amount::ZERO);
    assert_eq!(
        state.allowance_of(test_holder(), account).await.unwrap(),
        Amount::ZERO
    );
}

#[tokio::test(flavor = "multi_thread")]
async fn initial_liquidity_returns_stored_value() {
    let mut state = initialize_state();
    let liquidity = Liquidity {
        fungible_amount: Amount::from_tokens(1234),
        native_amount: Amount::from_tokens(10),
    };

    assert_eq!(state.initial_liquidity().await.unwrap(), None);

    state
        .initialize_liquidity(liquidity.clone(), test_chain_id(), false, None)
        .await
        .unwrap();

    assert_eq!(state.initial_liquidity().await.unwrap(), Some(liquidity));
}

#[tokio::test(flavor = "multi_thread")]
async fn approve_holder_to_owner_fails() {
    let mut state = initialize_state();

    let err = state
        .approve(test_holder(), test_owner(), Amount::ONE)
        .await
        .unwrap_err();
    assert!(matches!(err, StateError::InvalidOwner));
}

