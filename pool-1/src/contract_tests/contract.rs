use super::super::{PoolContract, PoolState};

use abi::{
    meme::MemeResponse,
    swap::pool::{
        InstantiationArgument, PoolAbi, PoolMessage, PoolOperation, PoolParameters, PoolResponse,
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
use pool::{FundRequest, FundStatus, FundType};
use std::str::FromStr;

use super::{PoolContract, PoolState};

#[tokio::test(flavor = "multi_thread")]
async fn create_pool_with_real_liquidity() {
    let pool = create_and_instantiate_pool(false).await;
    let _ = pool.state.pool();
}

#[tokio::test(flavor = "multi_thread")]
async fn create_pool_with_virtual_liquidity() {
    let pool = create_and_instantiate_pool(true).await;
    let _ = pool.state.pool();
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
async fn message_request_fund() {
    let mut pool = create_and_instantiate_pool(true).await;

    pool.execute_message(PoolMessage::RequestFund {
        token: pool.state.pool().token_0,
        transfer_id: 1000,
        amount: Amount::ONE,
    })
    .await;
}

#[tokio::test(flavor = "multi_thread")]
async fn message_fund_success() {
    let mut pool = create_and_instantiate_pool(true).await;
    let owner = Account {
        chain_id: pool.runtime.chain_id(),
        owner: pool.runtime.authenticated_signer().unwrap(),
    };

    let fund_request = FundRequest {
        from: owner,
        token: Some(pool.token_0()),
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

    let transfer_id = pool.state.create_fund_request(fund_request).unwrap();
    pool.execute_message(PoolMessage::FundSuccess { transfer_id })
        .await;

    let fund_request = pool.state.fund_request(transfer_id).await.unwrap();
    assert_eq!(fund_request.status, FundStatus::Success);
}

#[tokio::test(flavor = "multi_thread")]
async fn message_fund_fail() {
    let mut pool = create_and_instantiate_pool(true).await;
    let owner = Account {
        chain_id: pool.runtime.chain_id(),
        owner: pool.runtime.authenticated_signer().unwrap(),
    };

    let fund_request = FundRequest {
        from: owner,
        token: Some(pool.token_0()),
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

    let transfer_id = pool.state.create_fund_request(fund_request).unwrap();
    pool.execute_message(PoolMessage::FundFail {
        transfer_id,
        error: "Error".to_string(),
    })
    .await;

    let fund_request = pool.state.fund_request(transfer_id).await.unwrap();
    assert_eq!(fund_request.status, FundStatus::Fail);
    assert_eq!(fund_request.error, Some("Error".to_string()));
}

#[tokio::test(flavor = "multi_thread")]
async fn message_swap() {
    let mut pool = create_and_instantiate_pool(true).await;
    let owner = Account {
        chain_id: pool.runtime.chain_id(),
        owner: pool.runtime.authenticated_signer().unwrap(),
    };

    let reserve_0 = pool.state.reserve_0();
    let reserve_1 = pool.state.reserve_1();
    let swap_amount_0 = pool.state.calculate_swap_amount_0(Amount::ONE).unwrap();

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
        pool.state.reserve_0()
    );
    assert_eq!(
        reserve_1.try_add(Amount::ONE).unwrap(),
        pool.state.reserve_1()
    );
}

#[tokio::test(flavor = "multi_thread")]
async fn message_add_liquidity() {
    let mut pool = create_and_instantiate_pool(true).await;
    let owner = Account {
        chain_id: pool.runtime.chain_id(),
        owner: pool.runtime.authenticated_signer().unwrap(),
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
        pool.state.liquidity(owner).await.unwrap(),
        Amount::from_str("0.1").unwrap()
    );

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
        pool.state.liquidity(owner).await.unwrap(),
        Amount::from_str("0.05").unwrap()
    );
}

#[test]
fn cross_application_call() {}

fn mock_application_call(
    _authenticated: bool,
    _application_id: ApplicationId,
    _operation: Vec<u8>,
) -> Vec<u8> {
    bcs::to_bytes(&MemeResponse::Ok).unwrap()
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
        state: PoolState::load(runtime.root_view_storage_context())
            .blocking_wait()
            .expect("Failed to read from mock key value store"),
        runtime,
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
