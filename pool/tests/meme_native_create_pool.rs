// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

//! Integration tests for the Pool application.

#![cfg(not(target_arch = "wasm32"))]

use abi::{
    meme::MemeAbi,
    policy::open_chain_fee_budget,
    swap::{
        pool::{Pool, PoolAbi, PoolOperation},
        router::{Pool as PoolIndex, SwapAbi},
    },
};
use async_graphql::{Request, Variables};
use linera_sdk::{
    linera_base_types::{
        Account, AccountOwner, Amount, ApplicationId, BlobType, ChainDescription, ChainId,
    },
    test::{ActiveChain, MessageAction, QueryOutcome, TestValidator},
};
use pool::LiquidityAmount;
use serde_json::json;
use std::str::FromStr;

mod test_suite;
use test_suite::ProxyMemeSetup;

#[derive(Clone)]
struct TestSuite {
    setup: ProxyMemeSetup,

    validator: TestValidator,
    admin_chain: ActiveChain,
    meme_chain: ActiveChain,
    user_chain: ActiveChain,
    pool_chain: Option<ActiveChain>,
    swap_chain: ActiveChain,

    pool_application_id: Option<ApplicationId<PoolAbi>>,
    meme_application_id: Option<ApplicationId<MemeAbi>>,
    swap_application_id: Option<ApplicationId<SwapAbi>>,

    initial_liquidity: Amount,
    initial_native: Amount,
}

impl TestSuite {
    async fn new() -> Self {
        let setup = ProxyMemeSetup::new().await;
        let validator = setup.validator.clone();
        let admin_chain = setup.admin_chain.clone();
        let meme_chain = validator.new_chain().await;
        let user_chain = validator.new_chain().await; // New chain always has 10 token
        let swap_chain = setup.swap_chain.clone();
        let swap_application_id = Some(setup.swap_application_id);

        TestSuite {
            setup,

            validator,
            admin_chain,
            meme_chain,
            user_chain,
            pool_chain: None,
            swap_chain,

            pool_application_id: None,
            meme_application_id: None,
            swap_application_id,

            initial_liquidity: Amount::from_tokens(10),
            initial_native: Amount::from_tokens(10),
        }
    }

    fn chain_account(&self, chain: ActiveChain) -> Account {
        Account {
            chain_id: chain.id(),
            owner: AccountOwner::CHAIN,
        }
    }

    fn chain_owner_account(&self, chain: &ActiveChain) -> Account {
        Account {
            chain_id: chain.id(),
            owner: AccountOwner::from(chain.public_key()),
        }
    }

    fn application_account(&self, chain_id: ChainId, application_id: ApplicationId) -> Account {
        Account {
            chain_id,
            owner: AccountOwner::from(application_id.forget_abi()),
        }
    }

    async fn fund_chain(&self, chain: &ActiveChain, amount: Amount) {
        let (certificate, _) = self
            .admin_chain
            .add_block(|block| {
                block.with_native_token_transfer(
                    AccountOwner::CHAIN,
                    self.chain_account(chain.clone()),
                    amount,
                );
            })
            .await;
        chain
            .add_block(move |block| {
                block.with_messages_from_by_action(&certificate, MessageAction::Accept);
            })
            .await;
        chain.handle_received_messages().await;
    }

    async fn create_meme_application(&mut self) {
        let meme_user_chain = self.validator.new_chain().await;
        let (meme_chain, meme_application_id) = self
            .setup
            .create_meme_application(
                &meme_user_chain,
                false,
                false,
                None,
                Some(abi::meme::Liquidity {
                    fungible_amount: self.initial_liquidity,
                    native_amount: self.initial_native,
                }),
            )
            .await;
        self.meme_chain = meme_chain;
        self.meme_application_id = Some(meme_application_id);
    }

    async fn swap(&self, chain: &ActiveChain, buy_token_0: bool, amount: Amount) {
        chain
            .add_block(|block| {
                block.with_operation(
                    self.pool_application_id.unwrap(),
                    PoolOperation::Swap {
                        amount_0_in: if buy_token_0 { None } else { Some(amount) },
                        amount_1_in: if buy_token_0 { Some(amount) } else { None },
                        amount_0_out_min: None,
                        amount_1_out_min: None,
                        to: None,
                        block_timestamp: None,
                    },
                );
            })
            .await;
        self.meme_chain.handle_received_messages().await;
        chain.handle_received_messages().await;
        self.pool_chain
            .clone()
            .unwrap()
            .handle_received_messages()
            .await;
        self.pool_chain
            .clone()
            .unwrap()
            .handle_received_messages()
            .await;
        self.meme_chain.handle_received_messages().await;
        self.swap_chain.handle_received_messages().await;
        chain.handle_received_messages().await;
    }
}

/// Test setting a pool and testing its coherency across microchains.
///
/// Creates the application on a `chain`, initializing it with a 42 then adds 15 and obtains 57.
/// which is then checked.
#[tokio::test(flavor = "multi_thread")]
async fn meme_native_create_pool_test() {
    let _ = env_logger::builder().is_test(true).try_init();

    let mut suite = TestSuite::new().await;

    suite.create_meme_application().await;

    let meme_chain = &suite.meme_chain;
    let user_chain = &suite.user_chain;
    let swap_chain = &suite.swap_chain;

    let swap_key_pair = swap_chain.key_pair();

    // The meme app auto-creates its native pair pool via the LiquidityFunded path.
    // Process the cross-chain messages until the pool chain is created on the swap chain.
    meme_chain.handle_received_messages().await;
    let certificate = swap_chain.handle_received_messages().await;

    assert!(certificate.is_some());

    let (certificate, _) = certificate.unwrap();
    let block = certificate.inner().block();
    let description = block
        .created_blobs()
        .into_iter()
        .filter_map(|(blob_id, blob)| {
            (blob_id.blob_type == BlobType::ChainDescription)
                .then(|| bcs::from_bytes::<ChainDescription>(blob.content().bytes()).unwrap())
        })
        .next()
        .expect("swap should have created a pool chain");

    let pool_chain = ActiveChain::new(swap_key_pair.copy(), description, suite.clone().validator);
    suite.validator.add_chain(pool_chain.clone());
    suite.pool_chain = Some(pool_chain.clone());

    pool_chain.handle_received_messages().await;
    swap_chain.handle_received_messages().await;
    meme_chain.handle_received_messages().await;
    pool_chain.handle_received_messages().await;
    swap_chain.handle_received_messages().await;
    meme_chain.handle_received_messages().await;
    pool_chain.handle_received_messages().await;
    swap_chain.handle_received_messages().await;
    meme_chain.handle_received_messages().await;
    pool_chain.handle_received_messages().await;
    swap_chain.handle_received_messages().await;
    meme_chain.handle_received_messages().await;
    meme_chain.handle_received_messages().await;
    pool_chain.handle_received_messages().await;
    pool_chain.handle_received_messages().await;
    pool_chain.handle_received_messages().await;

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
            } }",
        )
        .await;
    assert_eq!(response["pools"].as_array().unwrap().len(), 1);
    let pool: PoolIndex =
        serde_json::from_value(response["pools"].as_array().unwrap()[0].clone()).unwrap();
    let pool_creator = pool.creator;

    let AccountOwner::Address32(application_description_hash) = pool.pool_application.owner else {
        panic!("Invalid pool application");
    };
    let pool_application_id = ApplicationId::new(application_description_hash);
    suite.pool_application_id = Some(pool_application_id.with_abi::<PoolAbi>());

    let QueryOutcome { response, .. } = pool_chain
        .graphql_query(suite.pool_application_id.unwrap(), "query { pool }")
        .await;
    let pool: Pool = serde_json::from_value(response["pool"].clone()).unwrap();

    assert_eq!(open_chain_fee_budget(), pool_chain.chain_balance().await);
    assert_eq!(suite.initial_liquidity, pool.reserve_0);
    assert_eq!(suite.initial_native, pool.reserve_1);

    let pool_application_account = suite.application_account(
        pool_chain.id(),
        suite.pool_application_id.unwrap().forget_abi(),
    );
    let query = Request::new(
        r#"
        query Balance($owner: Account!) {
            balanceOf(owner: $owner)
        }
        "#,
    )
    .variables(Variables::from_json(json!({
        "owner": {
            "chain_id": pool_application_account.chain_id.to_string(),
            "owner": pool_application_account.owner.to_string(),
        }
    })));
    let QueryOutcome { response, .. } = meme_chain
        .graphql_query(suite.meme_application_id.unwrap(), query)
        .await;
    assert_eq!(
        Amount::from_str(response["balanceOf"].as_str().unwrap()).unwrap(),
        suite.initial_liquidity,
    );

    // Swap
    let balance = Amount::from_str("20.1").unwrap();
    let budget = Amount::from_str("9.8").unwrap();
    let chain_initial_balance = Amount::from_str("10.0").unwrap();

    suite.fund_chain(&user_chain, balance).await;
    suite.swap(&user_chain, true, budget).await;

    assert_eq!(
        balance.try_sub(budget).unwrap(),
        user_chain
            .chain_balance()
            .await
            .try_sub(chain_initial_balance)
            .unwrap()
    );
    assert_eq!(open_chain_fee_budget(), pool_chain.chain_balance().await);
    assert_eq!(
        budget.try_add(suite.initial_native).unwrap(),
        pool_chain
            .owner_balance(&AccountOwner::from(pool_application_id))
            .await
            .unwrap()
    );

    let QueryOutcome { response, .. } = pool_chain
        .graphql_query(suite.pool_application_id.unwrap(), "query { pool }")
        .await;
    let pool: Pool = serde_json::from_value(response["pool"].clone()).unwrap();

    assert_eq!(open_chain_fee_budget(), pool_chain.chain_balance().await);
    assert_eq!(Amount::from_attos(19800000000000000000), pool.reserve_1);
    assert_eq!(Amount::from_attos(5058015437063113917), pool.reserve_0);

    let user_account = suite.chain_owner_account(&user_chain);
    let query = Request::new(
        r#"
        query Balance($owner: Account!) {
            balanceOf(owner: $owner)
        }
        "#,
    )
    .variables(Variables::from_json(json!({
        "owner": {
            "chain_id": user_account.chain_id.to_string(),
            "owner": user_account.owner.to_string(),
        }
    })));
    let QueryOutcome { response, .. } = meme_chain
        .graphql_query(suite.meme_application_id.unwrap(), query)
        .await;
    assert_eq!(
        Amount::from_str(response["balanceOf"].as_str().unwrap()).unwrap(),
        Amount::ZERO,
    );

    let query = Request::new(
        r#"
        query ClaimableBalance($token: ApplicationId, $owner: Account!) {
            claimableBalance(token: $token, owner: $owner)
        }
        "#,
    )
    .variables(Variables::from_json(json!({
        "token": suite.meme_application_id.unwrap().forget_abi().to_string(),
        "owner": {
            "chain_id": user_account.chain_id.to_string(),
            "owner": user_account.owner.to_string(),
        }
    })));
    let QueryOutcome { response, .. } = pool_chain
        .graphql_query(suite.pool_application_id.unwrap(), query)
        .await;
    assert_eq!(
        Amount::from_str(response["claimableBalance"].as_str().unwrap()).unwrap(),
        Amount::from_attos(4941984562936886083),
    );

    let query = Request::new(
        r#"
        query Balance($owner: Account!) {
            balanceOf(owner: $owner)
        }
        "#,
    )
    .variables(Variables::from_json(json!({
        "owner": {
            "chain_id": pool_application_account.chain_id.to_string(),
            "owner": pool_application_account.owner.to_string(),
        }
    })));
    let QueryOutcome { response, .. } = meme_chain
        .graphql_query(suite.meme_application_id.unwrap(), query)
        .await;
    assert_eq!(
        Amount::from_str(response["balanceOf"].as_str().unwrap()).unwrap(),
        suite.initial_liquidity,
    );

    let liquidity_fund_amount = Amount::from_attos(19800000000000000000);
    assert_eq!(
        liquidity_fund_amount,
        pool_chain
            .owner_balance(&AccountOwner::from(pool_application_id))
            .await
            .unwrap()
    );

    // Here meme balance should already add to pool application
    let query = Request::new(
        r#"
        query Balance($owner: Account!) {
            balanceOf(owner: $owner)
        }
        "#,
    )
    .variables(Variables::from_json(json!({
        "owner": {
            "chain_id": pool_application_account.chain_id.to_string(),
            "owner": pool_application_account.owner.to_string(),
        }
    })));
    let QueryOutcome { response, .. } = meme_chain
        .graphql_query(suite.meme_application_id.unwrap(), query)
        .await;
    assert_eq!(
        Amount::from_str(response["balanceOf"].as_str().unwrap()).unwrap(),
        suite.initial_liquidity,
    );

    let QueryOutcome { response, .. } = pool_chain
        .graphql_query(suite.pool_application_id.unwrap(), "query { pool }")
        .await;
    let pool: Pool = serde_json::from_value(response["pool"].clone()).unwrap();

    assert_eq!(open_chain_fee_budget(), pool_chain.chain_balance().await);
    // TODO: reserve should equal to balance ?
    assert_eq!(Amount::from_attos(19800000000000000000), pool.reserve_1);
    assert_eq!(Amount::from_attos(5058015437063113917), pool.reserve_0);

    let query = Request::new(
        r#"
        query Balance($owner: Account!) {
            balanceOf(owner: $owner)
        }
        "#,
    )
    .variables(Variables::from_json(json!({
        "owner": {
            "chain_id": user_account.chain_id.to_string(),
            "owner": user_account.owner.to_string(),
        }
    })));
    let QueryOutcome { response, .. } = meme_chain
        .graphql_query(suite.meme_application_id.unwrap(), query)
        .await;
    assert_eq!(
        Amount::from_str(response["balanceOf"].as_str().unwrap()).unwrap(),
        Amount::ZERO,
    );

    let query = Request::new(
        r#"
        query ClaimableBalance($token: ApplicationId, $owner: Account!) {
            claimableBalance(token: $token, owner: $owner)
        }
        "#,
    )
    .variables(Variables::from_json(json!({
        "token": suite.meme_application_id.unwrap().forget_abi().to_string(),
        "owner": {
            "chain_id": user_account.chain_id.to_string(),
            "owner": user_account.owner.to_string(),
        }
    })));
    let QueryOutcome { response, .. } = pool_chain
        .graphql_query(suite.pool_application_id.unwrap(), query)
        .await;
    assert_eq!(
        Amount::from_str(response["claimableBalance"].as_str().unwrap()).unwrap(),
        Amount::from_attos(4941984562936886083),
    );

    let query = Request::new(
        r#"
        query Liquidity($owner: Account!) {
            liquidity(owner: $owner) {
                liquidity
                amount0
                amount1
            }
        }
        "#,
    )
    .variables(Variables::from_json(json!({
        "owner": {
            "chain_id": pool_creator.chain_id.to_string(),
            "owner": pool_creator.owner.to_string(),
        }
    })));
    let QueryOutcome { response, .. } = pool_chain
        .graphql_query(suite.pool_application_id.unwrap(), query)
        .await;
    let liquidity: LiquidityAmount = serde_json::from_value(response["liquidity"].clone()).unwrap();
    assert_eq!(
        liquidity.liquidity,
        Amount::from_attos(10000000000000000000),
    );
}
