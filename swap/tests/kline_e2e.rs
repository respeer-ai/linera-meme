// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

//! End-to-end K-line tests for meme/native pools.

#![cfg(not(target_arch = "wasm32"))]

use abi::{
    hash::hash_cmp,
    meme::{
        InstantiationArgument as MemeInstantiationArgument, Liquidity, Meme, MemeAbi,
        MemeOperation, MemeParameters, Metadata, MiningBase, MiningInfo,
    },
    policy::open_chain_fee_budget,
    proxy::{InstantiationArgument as ProxyInstantiationArgument, ProxyAbi},
    store_type::StoreType,
    swap::{
        pool::{PoolAbi, PoolOperation},
        router::{
            InstantiationArgument as SwapInstantiationArgument, Pool as PoolIndex, SwapAbi,
            SwapParameters,
        },
        transaction::{Transaction, TransactionType},
    },
};
use linera_chain::types::ConfirmedBlockCertificate;
use linera_sdk::{
    linera_base_types::{
        Account, AccountOwner, Amount, ApplicationId, ApplicationPermissions, BlobType,
        ChainDescription, CryptoHash, ModuleId, TestString, TimeDelta, Timestamp,
    },
    test::{ActiveChain, MessageAction, QueryOutcome, TestValidator},
};
use std::{
    cmp::Ordering,
    str::FromStr,
    sync::{
        atomic::{AtomicBool, Ordering as AtomicOrdering},
        mpsc, Arc,
    },
    thread,
};

#[derive(Clone)]
struct TestSuite {
    validator: TestValidator,
    meme_chain: ActiveChain,
    swap_chain: ActiveChain,
    proxy_chain: Option<ActiveChain>,
    pool_chain: ActiveChain,
    maker_chains: Vec<ActiveChain>,
    meme_application_id: ApplicationId<MemeAbi>,
    pool_application_id: ApplicationId<PoolAbi>,
}

#[derive(Clone, Copy)]
struct TradeIntent {
    maker_index: usize,
    buy_token_0: bool,
    amount: Amount,
    time_secs: u64,
}

#[derive(Debug)]
struct KlineReport {
    trade_count: usize,
    buy_count: usize,
    sell_count: usize,
    longest_buy_streak: usize,
    longest_sell_streak: usize,
    max_same_timestamp_cluster: usize,
}

impl TestSuite {
    async fn new(enable_mining: bool) -> Self {
        let (validator, swap_bytecode_id) = TestValidator::with_current_module::<
            SwapAbi,
            SwapParameters,
            SwapInstantiationArgument,
        >()
        .await;

        validator.clock().set(Timestamp::from(0));

        let admin_chain = validator.get_chain(&validator.admin_chain_id());
        let mut swap_chain = validator.new_chain().await;
        let mut proxy_chain = if enable_mining {
            Some(validator.new_chain().await)
        } else {
            None
        };
        let meme_bytecode_id: ModuleId<MemeAbi, MemeParameters, MemeInstantiationArgument> =
            swap_chain.publish_bytecode_files_in("../meme").await;

        let pool_bytecode_id = swap_chain.publish_bytecode_files_in("../pool").await;
        let swap_application_id = swap_chain
            .create_application::<SwapAbi, SwapParameters, SwapInstantiationArgument>(
                swap_bytecode_id,
                SwapParameters {},
                SwapInstantiationArgument { pool_bytecode_id },
                vec![],
            )
            .await;

        let proxy_application_id = if let Some(proxy_chain) = proxy_chain.as_mut() {
            let proxy_bytecode_id = swap_chain.publish_bytecode_files_in("../proxy").await;
            Some(
                proxy_chain
                    .create_application::<ProxyAbi, (), ProxyInstantiationArgument>(
                        proxy_bytecode_id,
                        (),
                        ProxyInstantiationArgument {
                            meme_bytecode_id: meme_bytecode_id.forget_abi(),
                            operators: Vec::new(),
                            swap_application_id: swap_application_id.forget_abi(),
                        },
                        vec![],
                    )
                    .await,
            )
        } else {
            None
        };

        let mut meme_chain = if enable_mining {
            let proxy_application_id = proxy_application_id.unwrap().forget_abi();
            let swap_application_id = swap_application_id.forget_abi();
            let permissions = ApplicationPermissions {
                execute_operations: None,
                mandatory_applications: vec![],
                close_chain: vec![proxy_application_id, swap_application_id],
                change_application_permissions: vec![proxy_application_id, swap_application_id],
                call_service_as_oracle: Some(vec![proxy_application_id, swap_application_id]),
                make_http_requests: Some(vec![proxy_application_id, swap_application_id]),
            };
            validator
                .new_chain_with_application_permissions(permissions)
                .await
        } else {
            validator.new_chain().await
        };

        let maker_chains = vec![
            validator.new_chain().await,
            validator.new_chain().await,
            validator.new_chain().await,
        ];

        let initial_liquidity = Amount::from_tokens(11000000);
        let initial_native = Amount::from_tokens(10);
        let meme_application_id = meme_chain
            .create_application(
                meme_bytecode_id,
                MemeParameters {
                    creator: Self::chain_owner_account(&meme_chain),
                    initial_liquidity: Some(Liquidity {
                        fungible_amount: initial_liquidity,
                        native_amount: initial_native,
                    }),
                    virtual_initial_liquidity: true,
                    swap_creator_chain_id: swap_chain.id(),
                    enable_mining,
                    mining_supply: if enable_mining {
                        Some(Amount::from_tokens(10000000))
                    } else {
                        None
                    },
                },
                MemeInstantiationArgument {
                    meme: Meme {
                        name: "Test Token".to_string(),
                        ticker: "LTT".to_string(),
                        decimals: 6,
                        initial_supply: Amount::from_tokens(21000000),
                        total_supply: Amount::from_tokens(21000000),
                        metadata: Metadata {
                            logo_store_type: StoreType::S3,
                            logo: Some(CryptoHash::new(&TestString::new(
                                "Test Logo".to_string(),
                            ))),
                            description: "Test token description".to_string(),
                            twitter: None,
                            telegram: None,
                            discord: None,
                            website: None,
                            github: None,
                            live_stream: None,
                        },
                        virtual_initial_liquidity: true,
                        initial_liquidity: None,
                    },
                    blob_gateway_application_id: None,
                    ams_application_id: None,
                    proxy_application_id: proxy_application_id.map(|id| id.forget_abi()),
                    swap_application_id: Some(swap_application_id.forget_abi()),
                },
                vec![],
            )
            .await;

        if enable_mining {
            let proxy_application_id = proxy_application_id.unwrap().forget_abi();
            let swap_application_id = swap_application_id.forget_abi();
            let meme_application_id_raw = meme_application_id.forget_abi();
            let permissions = ApplicationPermissions {
                execute_operations: None,
                mandatory_applications: vec![],
                close_chain: vec![
                    proxy_application_id,
                    swap_application_id,
                    meme_application_id_raw,
                ],
                change_application_permissions: vec![
                    proxy_application_id,
                    swap_application_id,
                    meme_application_id_raw,
                ],
                call_service_as_oracle: Some(vec![
                    proxy_application_id,
                    swap_application_id,
                    meme_application_id_raw,
                ]),
                make_http_requests: Some(vec![
                    proxy_application_id,
                    swap_application_id,
                    meme_application_id_raw,
                ]),
            };
            meme_chain
                .add_block(|block| {
                    block.with_change_application_permissions(permissions);
                })
                .await;
        }

        meme_chain.handle_received_messages().await;
        if enable_mining {
            meme_chain.handle_received_messages().await;
            meme_chain.handle_received_messages().await;
        }
        let (certificate, _) = swap_chain
            .handle_received_messages()
            .await
            .expect("pool creation certificate should exist");
        let description = Self::extract_chain_description(&certificate);
        let pool_chain = ActiveChain::new(swap_chain.key_pair().copy(), description, validator.clone());
        validator.add_chain(pool_chain.clone());

        pool_chain.handle_received_messages().await;
        swap_chain.handle_received_messages().await;
        meme_chain.handle_received_messages().await;
        if enable_mining {
            pool_chain.handle_received_messages().await;
            swap_chain.handle_received_messages().await;
            meme_chain.handle_received_messages().await;
        }

        let QueryOutcome { response, .. } = swap_chain
            .graphql_query(
                swap_application_id,
                "query {
                    pools {
                        creator
                        poolId
                        token0
                        token1
                        poolApplication
                        createdAt
                    }
                }",
            )
            .await;
        let pool: PoolIndex =
            serde_json::from_value(response["pools"].as_array().unwrap()[0].clone()).unwrap();
        let AccountOwner::Address32(application_description_hash) = pool.pool_application.owner else {
            panic!("invalid pool application");
        };
        let pool_application_id = ApplicationId::new(application_description_hash).with_abi::<PoolAbi>();

        let funding_amount = open_chain_fee_budget()
            .try_add(Amount::from_str("20").unwrap())
            .unwrap();
        for maker_chain in &maker_chains {
            Self::fund_chain(&admin_chain, maker_chain, funding_amount).await;
        }

        Self {
            validator,
            meme_chain,
            swap_chain,
            proxy_chain,
            pool_chain,
            maker_chains,
            meme_application_id,
            pool_application_id,
        }
    }

    fn chain_account(chain: &ActiveChain) -> Account {
        Account {
            chain_id: chain.id(),
            owner: AccountOwner::CHAIN,
        }
    }

    fn chain_owner_account(chain: &ActiveChain) -> Account {
        Account {
            chain_id: chain.id(),
            owner: AccountOwner::from(chain.public_key()),
        }
    }

    async fn fund_chain(admin_chain: &ActiveChain, chain: &ActiveChain, amount: Amount) {
        let (certificate, _) = admin_chain
            .add_block(|block| {
                block.with_native_token_transfer(
                    AccountOwner::CHAIN,
                    Self::chain_account(chain),
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

    fn extract_chain_description(certificate: &ConfirmedBlockCertificate) -> ChainDescription {
        certificate
            .inner()
            .block()
            .created_blobs()
            .into_iter()
            .filter_map(|(blob_id, blob)| {
                (blob_id.blob_type == BlobType::ChainDescription)
                    .then(|| bcs::from_bytes::<ChainDescription>(blob.content().bytes()).unwrap())
            })
            .next()
            .unwrap()
    }

    fn timestamp_at(seconds: u64) -> Timestamp {
        Timestamp::from(0).saturating_add(TimeDelta::from_secs(seconds))
    }

    fn set_time(&self, seconds: u64) {
        self.validator.clock().set(Self::timestamp_at(seconds));
    }

    async fn latest_transactions(&self) -> Vec<Transaction> {
        let QueryOutcome { response, .. } = self
            .pool_chain
            .graphql_query(self.pool_application_id, "query { latestTransactions }")
            .await;
        serde_json::from_value(response["latestTransactions"].clone()).unwrap()
    }

    async fn mining_info(&self) -> MiningInfo {
        let QueryOutcome { response, .. } = self
            .meme_chain
            .graphql_query(
                self.meme_application_id,
                "query {
                    miningInfo {
                        initialTarget
                        target
                        blockDuration
                        targetBlockDuration
                        targetAdjustmentBlocks
                        emptyBlockRewardPercent
                        cumulativeBlocks
                        lastTargetAdjustedAt
                        initialRewardAmount
                        halvingCycle
                        nextHalvingAt
                        rewardAmount
                        miningHeight
                        miningExecutions
                        previousNonce
                        miningStarted
                    }
                }",
            )
            .await;
        serde_json::from_value(response["miningInfo"].clone()).unwrap()
    }

    async fn mine_pending_messages(
        &self,
        pending: &mut Vec<ConfirmedBlockCertificate>,
        time_secs: u64,
    ) {
        if pending.is_empty() {
            return;
        }

        let info = self.mining_info().await;
        let nonce = self.find_valid_nonce(&info);
        println!(
            "mine time={} pending_certificates={} mining_height={}",
            time_secs,
            pending.len(),
            info.mining_height.0
        );
        self.set_time(time_secs);

        let certificates = std::mem::take(pending);
        let (certificate, _) = self
            .meme_chain
            .add_block(|block| {
                block.with_operation(
                    self.meme_application_id,
                    MemeOperation::Mine { nonce },
                );
                for certificate in &certificates {
                    block.with_messages_from_by_action(certificate, MessageAction::Accept);
                }
            })
            .await;

        Box::pin(self.propagate_non_meme(certificate, time_secs, pending)).await;
    }

    async fn propagate_non_meme(
        &self,
        certificate: ConfirmedBlockCertificate,
        time_secs: u64,
        pending_meme: &mut Vec<ConfirmedBlockCertificate>,
    ) {
        if certificate
            .message_bundles_for(self.meme_chain.id())
            .next()
            .is_some()
        {
            pending_meme.push(certificate.clone());
        }

        let mut destinations = Vec::new();
        destinations.push(self.pool_chain.clone());
        destinations.push(self.swap_chain.clone());
        for chain in &self.maker_chains {
            destinations.push(chain.clone());
        }
        if let Some(proxy_chain) = &self.proxy_chain {
            destinations.push(proxy_chain.clone());
        }

        for chain in destinations {
            if certificate.message_bundles_for(chain.id()).next().is_none() {
                continue;
            }
            self.set_time(time_secs);
            let (next_certificate, _) = chain
                .add_block(|block| {
                    block.with_messages_from_by_action(&certificate, MessageAction::Accept);
                })
                .await;
            Box::pin(self.propagate_non_meme(next_certificate, time_secs, pending_meme)).await;
        }
    }

    async fn submit_trade(
        &self,
        trade: TradeIntent,
        pending_meme: &mut Vec<ConfirmedBlockCertificate>,
        mining_enabled: bool,
    ) {
        let chain = &self.maker_chains[trade.maker_index];
        self.set_time(trade.time_secs);
        let (certificate, _) = chain
            .add_block(|block| {
                block.with_operation(
                    self.pool_application_id,
                    PoolOperation::Swap {
                        amount_0_in: if trade.buy_token_0 {
                            None
                        } else {
                            Some(trade.amount)
                        },
                        amount_1_in: if trade.buy_token_0 {
                            Some(trade.amount)
                        } else {
                            None
                        },
                        amount_0_out_min: None,
                        amount_1_out_min: None,
                        to: None,
                        block_timestamp: None,
                    },
                );
            })
            .await;

        if mining_enabled {
            self.propagate_non_meme(certificate, trade.time_secs, pending_meme)
                .await;
        } else {
            let mut no_pending = Vec::new();
            self.propagate_non_meme(certificate, trade.time_secs, &mut no_pending)
                .await;
            while !no_pending.is_empty() {
                self.set_time(trade.time_secs);
                let certificates = std::mem::take(&mut no_pending);
                for certificate in certificates {
                    let (next_certificate, _) = self
                        .meme_chain
                        .add_block(|block| {
                            block.with_messages_from_by_action(&certificate, MessageAction::Accept);
                        })
                        .await;
                    self.propagate_non_meme(next_certificate, trade.time_secs, &mut no_pending)
                        .await;
                }
            }
        }
    }

    fn find_valid_nonce(&self, info: &MiningInfo) -> CryptoHash {
        let signer = AccountOwner::from(self.meme_chain.public_key());
        println!("search nonce height={}", info.mining_height.0);
        let workers = thread::available_parallelism()
            .map(|count| count.get())
            .unwrap_or(4)
            .min(8);
        let found = Arc::new(AtomicBool::new(false));
        let (sender, receiver) = mpsc::channel();
        let mut handles = Vec::with_capacity(workers);

        for worker in 0..workers {
            let found = found.clone();
            let sender = sender.clone();
            let height = info.mining_height;
            let chain_id = self.meme_chain.id();
            let previous_nonce = info.previous_nonce;
            let target = info.target;
            handles.push(thread::spawn(move || {
                let mut seed = worker as u64;
                let stride = workers as u64;
                while !found.load(AtomicOrdering::Relaxed) {
                    let mut nonce_bytes = [0u8; 32];
                    nonce_bytes[24..].copy_from_slice(&seed.to_be_bytes());
                    let nonce = CryptoHash::from(nonce_bytes);
                    let hash = CryptoHash::new(&MiningBase {
                        nonce,
                        height,
                        chain_id,
                        signer,
                        previous_nonce,
                    });
                    if matches!(hash_cmp(hash, target), Ordering::Less | Ordering::Equal) {
                        if !found.swap(true, AtomicOrdering::Relaxed) {
                            let _ = sender.send(nonce);
                        }
                        return;
                    }
                    seed = seed.saturating_add(stride);
                }
            }));
        }
        drop(sender);

        let nonce = receiver.recv().expect("parallel nonce search should succeed");
        found.store(true, AtomicOrdering::Relaxed);
        for handle in handles {
            let _ = handle.join();
        }
        nonce
    }
}

fn trade_plan() -> Vec<TradeIntent> {
    let times = [
        (0, true, 2),
        (1, true, 3),
        (2, true, 4),
        (0, false, 6),
        (1, false, 7),
        (2, false, 8),
        (0, true, 10),
        (1, false, 12),
        (2, true, 13),
        (0, false, 15),
        (1, true, 16),
        (2, false, 18),
        (0, true, 20),
        (1, false, 21),
        (2, true, 23),
        (0, false, 24),
        (1, true, 26),
        (2, false, 28),
    ];

    times
        .into_iter()
        .map(|(maker_index, buy_token_0, time_secs)| TradeIntent {
            maker_index,
            buy_token_0,
            amount: Amount::from_str("0.2").unwrap(),
            time_secs,
        })
        .collect()
}

fn build_report(transactions: &[Transaction]) -> KlineReport {
    let mut buy_count = 0;
    let mut sell_count = 0;
    let mut longest_buy_streak = 0;
    let mut longest_sell_streak = 0;
    let mut current_buy_streak = 0;
    let mut current_sell_streak = 0;
    let mut max_same_timestamp_cluster = 0;
    let mut current_cluster = 0;
    let mut previous_timestamp = None;

    for transaction in transactions.iter().filter(|transaction| {
        matches!(
            transaction.transaction_type,
            TransactionType::BuyToken0 | TransactionType::SellToken0
        )
    }) {
        if previous_timestamp == Some(transaction.created_at) {
            current_cluster += 1;
        } else {
            current_cluster = 1;
            previous_timestamp = Some(transaction.created_at);
        }
        max_same_timestamp_cluster = max_same_timestamp_cluster.max(current_cluster);

        match transaction.transaction_type {
            TransactionType::BuyToken0 => {
                buy_count += 1;
                current_buy_streak += 1;
                current_sell_streak = 0;
                longest_buy_streak = longest_buy_streak.max(current_buy_streak);
            }
            TransactionType::SellToken0 => {
                sell_count += 1;
                current_sell_streak += 1;
                current_buy_streak = 0;
                longest_sell_streak = longest_sell_streak.max(current_sell_streak);
            }
            _ => {}
        }
    }

    KlineReport {
        trade_count: buy_count + sell_count,
        buy_count,
        sell_count,
        longest_buy_streak,
        longest_sell_streak,
        max_same_timestamp_cluster,
    }
}

fn is_abnormal(report: &KlineReport) -> bool {
    if report.trade_count < 12 {
        return true;
    }

    let dominant = report.buy_count.max(report.sell_count) as f64 / report.trade_count as f64;
    let longest_streak = report.longest_buy_streak.max(report.longest_sell_streak);

    dominant >= 0.98 || longest_streak >= 16 || (longest_streak >= 10 && report.max_same_timestamp_cluster >= 8)
}

async fn run_kline_scenario(enable_mining: bool) -> KlineReport {
    println!("start scenario enable_mining={enable_mining}");
    let suite = TestSuite::new(enable_mining).await;
    println!("suite ready enable_mining={enable_mining}");
    let plan = trade_plan();
    let mut pending_meme = Vec::new();
    let mut next_mine_time = 5u64;

    for trade in plan {
        if enable_mining {
            while next_mine_time <= trade.time_secs {
                suite
                    .mine_pending_messages(&mut pending_meme, next_mine_time)
                    .await;
                next_mine_time += 5;
            }
        }

        suite
            .submit_trade(trade, &mut pending_meme, enable_mining)
            .await;
    }

    if enable_mining {
        while !pending_meme.is_empty() && next_mine_time <= 120 {
            suite
                .mine_pending_messages(&mut pending_meme, next_mine_time)
                .await;
            next_mine_time += 5;
        }
    }

    let transactions = suite.latest_transactions().await;
    let report = build_report(&transactions);
    println!(
        "enable_mining={} trade_count={} buy_count={} sell_count={} longest_buy_streak={} longest_sell_streak={} max_same_timestamp_cluster={}",
        enable_mining,
        report.trade_count,
        report.buy_count,
        report.sell_count,
        report.longest_buy_streak,
        report.longest_sell_streak,
        report.max_same_timestamp_cluster,
    );
    report
}

#[tokio::test(flavor = "multi_thread")]
#[ignore = "heavy mining e2e; run with CARGO_PROFILE_TEST_OPT_LEVEL=3"]
async fn kline_e2e_detects_no_pathological_shape_for_current_flow() {
    let _ = env_logger::builder().is_test(true).try_init();

    let no_mining = run_kline_scenario(false).await;
    assert!(
        !is_abnormal(&no_mining),
        "non-mining K-line should stay normal: {:?}",
        no_mining
    );

    let mining = run_kline_scenario(true).await;
    assert!(
        !is_abnormal(&mining),
        "mining K-line is abnormal: {:?}",
        mining
    );
}
