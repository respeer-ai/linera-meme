// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

//! Integration tests for the Swap application.

#![cfg(not(target_arch = "wasm32"))]

use abi::{meme::MemeAbi, policy::open_chain_fee_budget, swap::router::SwapAbi};
use async_graphql::{Request, Variables};
use linera_sdk::{
    linera_base_types::{Account, AccountOwner, Amount, ApplicationId, ChainId},
    test::{ActiveChain, QueryOutcome, TestValidator},
};
use serde_json::json;
use std::str::FromStr;

mod test_suite;
use test_suite::ProxyMemeSetup;

#[derive(Clone)]
struct TestSuite {
    pub setup: ProxyMemeSetup,

    pub validator: TestValidator,

    pub meme_chain: ActiveChain,
    pub swap_chain: ActiveChain,

    pub swap_application_id: Option<ApplicationId<SwapAbi>>,
    pub meme_application_id: Option<ApplicationId<MemeAbi>>,

    pub initial_native: Amount,
}

impl TestSuite {
    async fn new() -> Self {
        let setup = ProxyMemeSetup::new().await;
        let validator = setup.validator.clone();
        let swap_application_id = setup.swap_application_id;
        let meme_chain = validator.new_chain().await;
        let swap_chain = setup.swap_chain.clone();

        TestSuite {
            setup,

            validator,

            meme_chain,
            swap_chain,

            swap_application_id: Some(swap_application_id),
            meme_application_id: None,

            initial_native: Amount::from_tokens(10),
        }
    }

    fn application_account(&self, chain_id: ChainId, application_id: ApplicationId) -> Account {
        Account {
            chain_id,
            owner: AccountOwner::from(application_id.forget_abi()),
        }
    }

    async fn create_meme_application(&mut self, virtual_initial_liquidity: bool) {
        let meme_user_chain = self.validator.new_chain().await;
        let (meme_chain, meme_application_id) = self
            .setup
            .create_meme_application(&meme_user_chain, virtual_initial_liquidity, true, None)
            .await;
        self.meme_chain = meme_chain;
        self.meme_application_id = Some(meme_application_id);
    }
}

/// Test setting a swap and testing its coherency across microchains.
#[tokio::test(flavor = "multi_thread")]
async fn meme_native_pair_mining_full_supply_virtual_liquidity_test() {
    let _ = env_logger::builder().is_test(true).try_init();

    let mut suite = TestSuite::new().await;
    let swap_chain = suite.swap_chain.clone();

    suite.create_meme_application(true).await;
    let meme_chain = suite.meme_chain.clone();

    meme_chain.handle_received_messages().await;
    let certificate = swap_chain.handle_received_messages().await;

    assert!(certificate.is_some());

    let (certificate, _) = certificate.unwrap();
    let _block = certificate.inner().block();

    let meme_application_account = suite.application_account(
        meme_chain.id(),
        suite.meme_application_id.unwrap().forget_abi(),
    );
    let swap_application_account = suite.application_account(
        swap_chain.id(),
        suite.swap_application_id.unwrap().forget_abi(),
    );

    let query = Request::new(
        r#"
        query Allowance($owner: Account!, $spender: Account!) {
            allowanceOf(owner: $owner, spender: $spender)
        }
        "#,
    )
    .variables(Variables::from_json(json!({
        "owner": {
            "chain_id": meme_application_account.chain_id.to_string(),
            "owner": meme_application_account.owner.to_string(),
        },
        "spender": {
            "chain_id": swap_application_account.chain_id.to_string(),
            "owner": swap_application_account.owner.to_string(),
        }
    })));
    let QueryOutcome { response, .. } = meme_chain
        .graphql_query(suite.meme_application_id.unwrap(), query)
        .await;
    // No liquidity for full mining supply
    assert_eq!(
        Amount::from_str(response["allowanceOf"].as_str().unwrap()).unwrap(),
        Amount::ZERO,
    );

    swap_chain.handle_received_messages().await;
    meme_chain.handle_received_messages().await;

    let chain_initial_balance = Amount::from_str("10.0").unwrap();
    assert_eq!(meme_chain.chain_balance().await, open_chain_fee_budget());
    assert_eq!(
        swap_chain.chain_balance().await,
        chain_initial_balance
            .try_add(open_chain_fee_budget())
            .unwrap()
    );

    let QueryOutcome { response, .. } = swap_chain
        .graphql_query(
            suite.swap_application_id.unwrap(),
            "query { pools {
                creator
                poolId
                token0
                token1
                poolApplication
                createdAt
            }}",
        )
        .await;
    assert_eq!(response["pools"].as_array().unwrap().len(), 0);

    let query = Request::new(
        r#"
        query Allowance($owner: Account!, $spender: Account!) {
            allowanceOf(owner: $owner, spender: $spender)
        }
        "#,
    )
    .variables(Variables::from_json(json!({
        "owner": {
            "chain_id": meme_application_account.chain_id.to_string(),
            "owner": meme_application_account.owner.to_string(),
        },
        "spender": {
            "chain_id": swap_application_account.chain_id.to_string(),
            "owner": swap_application_account.owner.to_string(),
        }
    })));
    let QueryOutcome { response, .. } = meme_chain
        .graphql_query(suite.meme_application_id.unwrap(), query)
        .await;
    assert_eq!(
        Amount::from_str(response["allowanceOf"].as_str().unwrap()).unwrap(),
        Amount::ZERO,
    );
}

#[tokio::test(flavor = "multi_thread")]
async fn meme_native_pair_mining_full_supply_real_liquidity_test() {
    let _ = env_logger::builder().is_test(true).try_init();

    let mut suite = TestSuite::new().await;
    let swap_chain = suite.swap_chain.clone();

    suite.create_meme_application(false).await;
    let meme_chain = suite.meme_chain.clone();

    meme_chain.handle_received_messages().await;
    let certificate = swap_chain.handle_received_messages().await;

    assert!(certificate.is_some());

    let (certificate, _) = certificate.unwrap();
    let _block = certificate.inner().block();

    let meme_application_account = suite.application_account(
        meme_chain.id(),
        suite.meme_application_id.unwrap().forget_abi(),
    );
    let swap_application_account = suite.application_account(
        swap_chain.id(),
        suite.swap_application_id.unwrap().forget_abi(),
    );

    let query = Request::new(
        r#"
        query Allowance($owner: Account!, $spender: Account!) {
            allowanceOf(owner: $owner, spender: $spender)
        }
        "#,
    )
    .variables(Variables::from_json(json!({
        "owner": {
            "chain_id": meme_application_account.chain_id.to_string(),
            "owner": meme_application_account.owner.to_string(),
        },
        "spender": {
            "chain_id": swap_application_account.chain_id.to_string(),
            "owner": swap_application_account.owner.to_string(),
        }
    })));
    let QueryOutcome { response, .. } = meme_chain
        .graphql_query(suite.meme_application_id.unwrap(), query)
        .await;
    // No liquidity for full mining supply
    assert_eq!(
        Amount::from_str(response["allowanceOf"].as_str().unwrap()).unwrap(),
        Amount::ZERO,
    );

    assert_eq!(
        swap_chain
            .owner_balance(
                &suite
                    .application_account(
                        swap_chain.id(),
                        suite.swap_application_id.unwrap().forget_abi()
                    )
                    .owner
            )
            .await,
        Some(suite.initial_native)
    );
    let chain_initial_balance = Amount::from_str("10.0").unwrap();
    assert_eq!(meme_chain.chain_balance().await, open_chain_fee_budget());
    assert_eq!(
        swap_chain.chain_balance().await,
        chain_initial_balance
            .try_add(open_chain_fee_budget())
            .unwrap()
    );

    swap_chain.handle_received_messages().await;
    meme_chain.handle_received_messages().await;

    assert_eq!(meme_chain.chain_balance().await, open_chain_fee_budget());
    assert_eq!(
        swap_chain.chain_balance().await,
        chain_initial_balance
            .try_add(open_chain_fee_budget())
            .unwrap()
    );

    let QueryOutcome { response, .. } = swap_chain
        .graphql_query(
            suite.swap_application_id.unwrap(),
            "query { pools {
                creator
                poolId
                token0
                token1
                poolApplication
                createdAt
            }}",
        )
        .await;
    assert_eq!(response["pools"].as_array().unwrap().len(), 0);

    let query = Request::new(
        r#"
        query Allowance($owner: Account!, $spender: Account!) {
            allowanceOf(owner: $owner, spender: $spender)
        }
        "#,
    )
    .variables(Variables::from_json(json!({
        "owner": {
            "chain_id": meme_application_account.chain_id.to_string(),
            "owner": meme_application_account.owner.to_string(),
        },
        "spender": {
            "chain_id": swap_application_account.chain_id.to_string(),
            "owner": swap_application_account.owner.to_string(),
        }
    })));
    let QueryOutcome { response, .. } = meme_chain
        .graphql_query(suite.meme_application_id.unwrap(), query)
        .await;
    assert_eq!(
        Amount::from_str(response["allowanceOf"].as_str().unwrap()).unwrap(),
        Amount::ZERO,
    );
}
