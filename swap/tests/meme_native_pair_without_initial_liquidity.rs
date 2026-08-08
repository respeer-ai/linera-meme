// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

//! Integration tests for the Pool application.

#![cfg(not(target_arch = "wasm32"))]

use abi::{
    meme::MemeAbi,
    policy::open_chain_fee_budget,
    swap::router::{SwapAbi, SwapOperation},
};
use linera_sdk::{
    linera_base_types::{Account, AccountOwner, Amount, ApplicationId, BlobType, ChainDescription},
    test::{ActiveChain, MessageAction, QueryOutcome, TestValidator},
};

mod test_suite;
use test_suite::ProxyMemeSetup;

#[derive(Clone)]
struct TestSuite {
    setup: ProxyMemeSetup,

    validator: TestValidator,
    admin_chain: ActiveChain,
    meme_chain: ActiveChain,
    user_chain: ActiveChain,
    swap_chain: ActiveChain,

    meme_application_id: Option<ApplicationId<MemeAbi>>,
    swap_application_id: Option<ApplicationId<SwapAbi>>,
}

impl TestSuite {
    async fn new() -> Self {
        let setup = ProxyMemeSetup::new().await;
        let validator = setup.validator.clone();
        let admin_chain = setup.admin_chain.clone();
        let swap_application_id = setup.swap_application_id;
        let user_chain = validator.new_chain().await;
        let swap_chain = setup.swap_chain.clone();

        TestSuite {
            setup,

            validator,
            admin_chain,
            meme_chain: user_chain.clone(),
            user_chain,
            swap_chain,

            meme_application_id: None,
            swap_application_id: Some(swap_application_id),
        }
    }

    fn chain_account(&self, chain: ActiveChain) -> Account {
        Account {
            chain_id: chain.id(),
            owner: AccountOwner::CHAIN,
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
            .create_meme_application(&meme_user_chain, true, false, None)
            .await;
        self.meme_chain = meme_chain;
        self.meme_application_id = Some(meme_application_id);
    }

    async fn create_pool(
        &self,
        chain: &ActiveChain,
        amount_0: Amount,
        amount_1: Amount,
    ) -> ChainDescription {
        chain
            .add_block(|block| {
                block.with_operation(
                    self.swap_application_id.unwrap(),
                    SwapOperation::CreatePool {
                        token_0: self.meme_application_id.unwrap().forget_abi(),
                        token_1: None,
                        amount_0,
                        amount_1,
                        to: None,
                    },
                );
            })
            .await;
        let certificate = self.swap_chain.handle_received_messages().await;
        chain.handle_received_messages().await;
        chain.handle_received_messages().await;
        chain.handle_received_messages().await;
        self.meme_chain.handle_received_messages().await;

        assert!(certificate.is_some());

        let (certificate, _) = certificate.unwrap();
        let block = certificate.inner().block();
        block
            .created_blobs()
            .into_iter()
            .filter_map(|(blob_id, blob)| {
                (blob_id.blob_type == BlobType::ChainDescription)
                    .then(|| bcs::from_bytes::<ChainDescription>(blob.content().bytes()).unwrap())
            })
            .next()
            .unwrap()
    }
}

/// Test setting a pool and testing its coherency across microchains.
///
/// Creates the application on a `chain`, initializing it with a 42 then adds 15 and obtains 57.
/// which is then checked.
#[tokio::test(flavor = "multi_thread")]
async fn meme_native_pair_without_initial_liquidity_test() {
    let _ = env_logger::builder().is_test(true).try_init();

    let mut suite = TestSuite::new().await;
    let meme_chain = &suite.meme_chain.clone();
    let user_chain = &suite.user_chain.clone();
    let swap_chain = &suite.swap_chain.clone();

    let swap_key_pair = swap_chain.key_pair();

    suite
        .fund_chain(&meme_chain, open_chain_fee_budget().try_mul(2).unwrap())
        .await;
    suite
        .fund_chain(
            &user_chain,
            open_chain_fee_budget()
                .try_add(Amount::from_tokens(10))
                .unwrap(),
        )
        .await;

    suite.create_meme_application().await;

    // Check initial swap pool
    meme_chain.handle_received_messages().await;
    swap_chain.handle_received_messages().await;
    swap_chain.handle_received_messages().await;

    // Only meme chain has meme balance right now
    let description = suite
        .create_pool(&meme_chain, Amount::ONE, Amount::ONE)
        .await;

    let pool_chain = ActiveChain::new(swap_key_pair.copy(), description, suite.clone().validator);
    pool_chain.handle_received_messages().await;

    suite.validator.add_chain(pool_chain.clone());

    swap_chain.handle_received_messages().await;

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

    pool_chain.handle_received_messages().await;
    meme_chain.handle_received_messages().await;
    swap_chain.handle_received_messages().await;

    // TODO: transfer one to user then create pool
}
