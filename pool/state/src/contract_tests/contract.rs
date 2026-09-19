use super::super::PoolStateContract;
use abi::pool::state_v1::{
    PoolStateAbi, PoolStateV1Operation, PoolStateV1Response, StateInstantiationArgument,
};
use abi::pool::Pool;
use linera_sdk::{
    linera_base_types::{
        Account, AccountOwner, Amount, ApplicationDescription, ApplicationId, BlockHeight, ChainId,
        CryptoHash, ModuleId, Timestamp,
    },
    util::BlockingWait,
    views::View,
    Contract, ContractRuntime,
};
use pool_state::state::PoolState;
use std::{cell::RefCell, rc::Rc, str::FromStr};

struct TestSuite {
    contract: PoolStateContract,
}

impl TestSuite {
    fn new() -> Self {
        let runtime = Self::runtime();
        let mut contract = PoolStateContract {
            state: Rc::new(RefCell::new(
                PoolState::load(runtime.root_view_storage_context())
                    .blocking_wait()
                    .expect("Failed to load pool state v1"),
            )),
            runtime: Rc::new(RefCell::new(runtime)),
        };
        contract
            .instantiate(StateInstantiationArgument {
                business_application_id: Self::business_application_id(),
                operator: Some(Self::operator()),
            })
            .blocking_wait();
        Self { contract }
    }

    async fn execute_operation(&mut self, operation: PoolStateV1Operation) -> PoolStateV1Response {
        self.contract.execute_operation(operation).await
    }

    async fn initialize(&mut self) {
        self.execute_operation(PoolStateV1Operation::Initialize {
            pool: Self::pool(),
            router_application_id: Self::business_application_id(),
        })
        .await;
    }

    fn set_chain_id(&mut self, chain_id: ChainId) {
        self.contract.runtime.borrow_mut().set_chain_id(chain_id);
    }

    fn set_application_creator_chain_id(&mut self, chain_id: ChainId) {
        self.contract
            .runtime
            .borrow_mut()
            .set_application_creator_chain_id(chain_id);
    }

    fn set_authenticated_caller(&mut self, caller: ApplicationId) {
        self.contract
            .runtime
            .borrow_mut()
            .set_authenticated_caller_id(caller);
    }

    fn runtime() -> ContractRuntime<PoolStateContract> {
        ContractRuntime::new()
            .with_application_parameters(())
            .with_authenticated_caller_id(Self::business_application_id())
            .with_chain_id(Self::chain_id())
            .with_application_creator_chain_id(Self::chain_id())
            .with_application_description(
                Self::business_application_id(),
                Self::application_description(Self::chain_id()),
            )
            .with_application_description(
                Self::other_business_application_id(),
                Self::application_description(Self::chain_id()),
            )
            .with_application_id(Self::state_application_id().with_abi::<PoolStateAbi>())
            .with_system_time(Timestamp::from(1))
            .with_block_height(BlockHeight::from(1))
    }

    fn application_description(creator_chain_id: ChainId) -> ApplicationDescription {
        ApplicationDescription {
            module_id: ModuleId::from_str("b94e486abcfc016e937dad4297523060095f405530c95d498d981a94141589f167693295a14c3b48460ad6f75d67d2414428227550eb8cee8ecaa37e8646518300").unwrap(),
            creator_chain_id,
            block_height: BlockHeight::from(1),
            application_index: 0,
            parameters: Vec::new(),
            required_application_ids: Vec::new(),
        }
    }

    fn operator() -> Account {
        Account {
            chain_id: Self::chain_id(),
            owner: AccountOwner::from_str(
                "0x02e900512d2fca22897f80a2f6932ff454f2752ef7afad18729dd25e5b5b6e00",
            )
            .unwrap(),
        }
    }

    fn other_account() -> Account {
        Account {
            chain_id: Self::chain_id(),
            owner: AccountOwner::from_str(
                "0x5279b3ae14d3b38e14b65a74aefe44824ea88b25c7841836e9ec77d991a5bc8f",
            )
            .unwrap(),
        }
    }

    fn chain_id() -> ChainId {
        ChainId(
            CryptoHash::from_str(
                "a10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5baa",
            )
            .unwrap(),
        )
    }

    fn other_chain_id() -> ChainId {
        ChainId(
            CryptoHash::from_str(
                "a20ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5baa",
            )
            .unwrap(),
        )
    }

    fn business_application_id() -> ApplicationId {
        Self::application_id("b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bad")
    }

    fn other_business_application_id() -> ApplicationId {
        Self::application_id("b20ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bad")
    }

    fn state_application_id() -> ApplicationId {
        Self::application_id("b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5baf")
    }

    fn token_0() -> ApplicationId {
        Self::application_id("b30ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bad")
    }

    fn application_id(hex: &str) -> ApplicationId {
        ApplicationId::from_str(hex).unwrap()
    }

    fn pool() -> Pool {
        Pool::create(
            Self::token_0(),
            None,
            30,
            Self::operator(),
            Timestamp::from(1),
        )
    }
}

#[tokio::test(flavor = "multi_thread")]
async fn initialize_succeeds_on_creator_chain() {
    let mut suite = TestSuite::new();

    let response = suite
        .execute_operation(PoolStateV1Operation::Initialize {
            pool: TestSuite::pool(),
            router_application_id: TestSuite::business_application_id(),
        })
        .await;

    assert_eq!(response, PoolStateV1Response::Ok);

    let response = suite.execute_operation(PoolStateV1Operation::Pool).await;
    assert_eq!(response, PoolStateV1Response::Pool(TestSuite::pool()));

    let response = suite
        .execute_operation(PoolStateV1Operation::RouterApplicationId)
        .await;
    assert_eq!(
        response,
        PoolStateV1Response::RouterApplicationId(TestSuite::business_application_id())
    );
}

#[tokio::test(flavor = "multi_thread")]
async fn initialize_rejects_duplicate_initialization() {
    let mut suite = TestSuite::new();
    suite.initialize().await;

    let response = suite
        .execute_operation(PoolStateV1Operation::Initialize {
            pool: TestSuite::pool(),
            router_application_id: TestSuite::business_application_id(),
        })
        .await;

    assert!(matches!(response, PoolStateV1Response::Fail(_)));
}

#[tokio::test(flavor = "multi_thread")]
async fn initialize_rejects_non_creator_chain() {
    let mut suite = TestSuite::new();
    suite.set_chain_id(TestSuite::other_chain_id());
    suite.set_application_creator_chain_id(TestSuite::chain_id());

    let response = suite
        .execute_operation(PoolStateV1Operation::Initialize {
            pool: TestSuite::pool(),
            router_application_id: TestSuite::business_application_id(),
        })
        .await;

    assert!(matches!(response, PoolStateV1Response::Fail(_)));
}

#[tokio::test(flavor = "multi_thread")]
async fn initialize_rejects_unbound_business_app() {
    let mut suite = TestSuite::new();
    suite.set_authenticated_caller(TestSuite::other_business_application_id());

    let response = suite
        .execute_operation(PoolStateV1Operation::Initialize {
            pool: TestSuite::pool(),
            router_application_id: TestSuite::business_application_id(),
        })
        .await;

    assert!(matches!(response, PoolStateV1Response::Fail(_)));
}

#[tokio::test(flavor = "multi_thread")]
async fn mint_shares_increases_total_supply_and_liquidity() {
    let mut suite = TestSuite::new();
    suite.initialize().await;

    let response = suite
        .execute_operation(PoolStateV1Operation::MintShares {
            to: TestSuite::operator(),
            amount: Amount::from_tokens(100),
        })
        .await;
    assert_eq!(response, PoolStateV1Response::Ok);

    let response = suite
        .execute_operation(PoolStateV1Operation::TotalSupply)
        .await;
    assert_eq!(
        response,
        PoolStateV1Response::TotalSupply(Amount::from_tokens(100))
    );

    let response = suite
        .execute_operation(PoolStateV1Operation::Liquidity {
            account: TestSuite::operator(),
        })
        .await;
    assert_eq!(
        response,
        PoolStateV1Response::Liquidity(Amount::from_tokens(100))
    );
}

#[tokio::test(flavor = "multi_thread")]
async fn burn_shares_decreases_total_supply_and_liquidity() {
    let mut suite = TestSuite::new();
    suite.initialize().await;
    suite
        .execute_operation(PoolStateV1Operation::MintShares {
            to: TestSuite::operator(),
            amount: Amount::from_tokens(100),
        })
        .await;

    let response = suite
        .execute_operation(PoolStateV1Operation::BurnShares {
            from: TestSuite::operator(),
            amount: Amount::from_tokens(40),
        })
        .await;
    assert_eq!(response, PoolStateV1Response::Ok);

    let response = suite
        .execute_operation(PoolStateV1Operation::TotalSupply)
        .await;
    assert_eq!(
        response,
        PoolStateV1Response::TotalSupply(Amount::from_tokens(60))
    );

    let response = suite
        .execute_operation(PoolStateV1Operation::Liquidity {
            account: TestSuite::operator(),
        })
        .await;
    assert_eq!(
        response,
        PoolStateV1Response::Liquidity(Amount::from_tokens(60))
    );
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic(expected = "Invalid liquidity")]
async fn burn_shares_rejects_amount_exceeding_share() {
    let mut suite = TestSuite::new();
    suite.initialize().await;
    suite
        .execute_operation(PoolStateV1Operation::MintShares {
            to: TestSuite::operator(),
            amount: Amount::from_tokens(100),
        })
        .await;
    suite
        .execute_operation(PoolStateV1Operation::MintShares {
            to: TestSuite::other_account(),
            amount: Amount::from_tokens(100),
        })
        .await;

    suite
        .execute_operation(PoolStateV1Operation::BurnShares {
            from: TestSuite::operator(),
            amount: Amount::from_tokens(150),
        })
        .await;
}

#[tokio::test(flavor = "multi_thread")]
async fn burn_shares_rejects_amount_exceeding_total_supply() {
    let mut suite = TestSuite::new();
    suite.initialize().await;
    suite
        .execute_operation(PoolStateV1Operation::MintShares {
            to: TestSuite::operator(),
            amount: Amount::from_tokens(100),
        })
        .await;

    let response = suite
        .execute_operation(PoolStateV1Operation::BurnShares {
            from: TestSuite::operator(),
            amount: Amount::from_tokens(101),
        })
        .await;

    assert!(matches!(response, PoolStateV1Response::Fail(_)));
}

#[tokio::test(flavor = "multi_thread")]
async fn burn_shares_rejects_unbound_business_app() {
    let mut suite = TestSuite::new();
    suite.initialize().await;
    suite.set_authenticated_caller(TestSuite::other_business_application_id());

    let response = suite
        .execute_operation(PoolStateV1Operation::BurnShares {
            from: TestSuite::operator(),
            amount: Amount::from_tokens(1),
        })
        .await;

    assert!(matches!(response, PoolStateV1Response::Fail(_)));
}

#[tokio::test(flavor = "multi_thread")]
async fn claim_moves_claimable_to_claiming() {
    let mut suite = TestSuite::new();
    suite.initialize().await;
    suite
        .execute_operation(PoolStateV1Operation::CreditClaimable {
            token: Some(TestSuite::token_0()),
            owner: TestSuite::operator(),
            amount: Amount::from_tokens(10),
        })
        .await;

    let response = suite
        .execute_operation(PoolStateV1Operation::Claim {
            token: Some(TestSuite::token_0()),
            owner: TestSuite::operator(),
            amount: Amount::from_tokens(4),
        })
        .await;
    assert_eq!(response, PoolStateV1Response::Ok);

    let response = suite
        .execute_operation(PoolStateV1Operation::ClaimableBalance {
            token: Some(TestSuite::token_0()),
            owner: TestSuite::operator(),
        })
        .await;
    assert_eq!(
        response,
        PoolStateV1Response::ClaimableBalance(Amount::from_tokens(6))
    );
    let response = suite
        .execute_operation(PoolStateV1Operation::ClaimingBalance {
            token: Some(TestSuite::token_0()),
            owner: TestSuite::operator(),
        })
        .await;
    assert_eq!(
        response,
        PoolStateV1Response::ClaimingBalance(Amount::from_tokens(4))
    );
}

#[tokio::test(flavor = "multi_thread")]
async fn credit_claimable_accumulates_multiple_credits() {
    let mut suite = TestSuite::new();
    suite.initialize().await;
    for _ in 0..2 {
        suite
            .execute_operation(PoolStateV1Operation::CreditClaimable {
                token: Some(TestSuite::token_0()),
                owner: TestSuite::operator(),
                amount: Amount::from_tokens(5),
            })
            .await;
    }

    let response = suite
        .execute_operation(PoolStateV1Operation::ClaimableBalance {
            token: Some(TestSuite::token_0()),
            owner: TestSuite::operator(),
        })
        .await;
    assert_eq!(
        response,
        PoolStateV1Response::ClaimableBalance(Amount::from_tokens(10))
    );
}

#[tokio::test(flavor = "multi_thread")]
async fn claim_success_consumes_claiming() {
    let mut suite = TestSuite::new();
    suite.initialize().await;
    suite
        .execute_operation(PoolStateV1Operation::CreditClaimable {
            token: Some(TestSuite::token_0()),
            owner: TestSuite::operator(),
            amount: Amount::from_tokens(10),
        })
        .await;
    suite
        .execute_operation(PoolStateV1Operation::Claim {
            token: Some(TestSuite::token_0()),
            owner: TestSuite::operator(),
            amount: Amount::from_tokens(4),
        })
        .await;

    let response = suite
        .execute_operation(PoolStateV1Operation::ClaimSuccess {
            token: Some(TestSuite::token_0()),
            owner: TestSuite::operator(),
            amount: Amount::from_tokens(4),
        })
        .await;
    assert_eq!(response, PoolStateV1Response::Ok);

    let response = suite
        .execute_operation(PoolStateV1Operation::ClaimingBalance {
            token: Some(TestSuite::token_0()),
            owner: TestSuite::operator(),
        })
        .await;
    assert_eq!(
        response,
        PoolStateV1Response::ClaimingBalance(Amount::ZERO)
    );
}

#[tokio::test(flavor = "multi_thread")]
async fn claim_fail_returns_amount_to_claimable() {
    let mut suite = TestSuite::new();
    suite.initialize().await;
    suite
        .execute_operation(PoolStateV1Operation::CreditClaimable {
            token: Some(TestSuite::token_0()),
            owner: TestSuite::operator(),
            amount: Amount::from_tokens(10),
        })
        .await;
    suite
        .execute_operation(PoolStateV1Operation::Claim {
            token: Some(TestSuite::token_0()),
            owner: TestSuite::operator(),
            amount: Amount::from_tokens(4),
        })
        .await;

    let response = suite
        .execute_operation(PoolStateV1Operation::ClaimFail {
            token: Some(TestSuite::token_0()),
            owner: TestSuite::operator(),
            amount: Amount::from_tokens(4),
        })
        .await;
    assert_eq!(response, PoolStateV1Response::Ok);

    let response = suite
        .execute_operation(PoolStateV1Operation::ClaimableBalance {
            token: Some(TestSuite::token_0()),
            owner: TestSuite::operator(),
        })
        .await;
    assert_eq!(
        response,
        PoolStateV1Response::ClaimableBalance(Amount::from_tokens(10))
    );
    let response = suite
        .execute_operation(PoolStateV1Operation::ClaimingBalance {
            token: Some(TestSuite::token_0()),
            owner: TestSuite::operator(),
        })
        .await;
    assert_eq!(
        response,
        PoolStateV1Response::ClaimingBalance(Amount::ZERO)
    );
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic(expected = "Insufficient claimable balance")]
async fn claim_rejects_amount_exceeding_claimable() {
    let mut suite = TestSuite::new();
    suite.initialize().await;
    suite
        .execute_operation(PoolStateV1Operation::CreditClaimable {
            token: Some(TestSuite::token_0()),
            owner: TestSuite::operator(),
            amount: Amount::from_tokens(10),
        })
        .await;

    suite
        .execute_operation(PoolStateV1Operation::Claim {
            token: Some(TestSuite::token_0()),
            owner: TestSuite::operator(),
            amount: Amount::from_tokens(11),
        })
        .await;
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic(expected = "Insufficient claiming balance")]
async fn claim_success_rejects_amount_exceeding_claiming() {
    let mut suite = TestSuite::new();
    suite.initialize().await;
    suite
        .execute_operation(PoolStateV1Operation::CreditClaimable {
            token: Some(TestSuite::token_0()),
            owner: TestSuite::operator(),
            amount: Amount::from_tokens(10),
        })
        .await;
    suite
        .execute_operation(PoolStateV1Operation::Claim {
            token: Some(TestSuite::token_0()),
            owner: TestSuite::operator(),
            amount: Amount::from_tokens(4),
        })
        .await;

    suite
        .execute_operation(PoolStateV1Operation::ClaimSuccess {
            token: Some(TestSuite::token_0()),
            owner: TestSuite::operator(),
            amount: Amount::from_tokens(5),
        })
        .await;
}

#[tokio::test(flavor = "multi_thread")]
async fn claim_rejects_unbound_business_app() {
    let mut suite = TestSuite::new();
    suite.initialize().await;
    suite.set_authenticated_caller(TestSuite::other_business_application_id());

    let response = suite
        .execute_operation(PoolStateV1Operation::Claim {
            token: Some(TestSuite::token_0()),
            owner: TestSuite::operator(),
            amount: Amount::from_tokens(1),
        })
        .await;

    assert!(matches!(response, PoolStateV1Response::Fail(_)));
}

#[tokio::test(flavor = "multi_thread")]
async fn set_fee_to_updates_fee_receiver_for_current_fee_to_setter() {
    let mut suite = TestSuite::new();
    suite.initialize().await;

    let response = suite
        .execute_operation(PoolStateV1Operation::SetFeeTo {
            operator: TestSuite::operator(),
            account: TestSuite::other_account(),
        })
        .await;
    assert_eq!(response, PoolStateV1Response::Ok);

    let response = suite.execute_operation(PoolStateV1Operation::Pool).await;
    let PoolStateV1Response::Pool(pool) = response else {
        panic!("Unexpected response");
    };
    assert_eq!(pool.fee_to, TestSuite::other_account());
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic(expected = "Invalid operator")]
async fn set_fee_to_rejects_non_fee_to_setter() {
    let mut suite = TestSuite::new();
    suite.initialize().await;

    suite
        .execute_operation(PoolStateV1Operation::SetFeeTo {
            operator: TestSuite::other_account(),
            account: TestSuite::other_account(),
        })
        .await;
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic(expected = "Invalid operator")]
async fn set_fee_to_setter_rotation_invalidates_old_operator() {
    let mut suite = TestSuite::new();
    suite.initialize().await;
    suite
        .execute_operation(PoolStateV1Operation::SetFeeToSetter {
            operator: TestSuite::operator(),
            account: TestSuite::other_account(),
        })
        .await;

    suite
        .execute_operation(PoolStateV1Operation::SetFeeTo {
            operator: TestSuite::operator(),
            account: TestSuite::operator(),
        })
        .await;
}

#[tokio::test(flavor = "multi_thread")]
async fn build_transaction_assigns_incrementing_ids() {
    let mut suite = TestSuite::new();
    suite.initialize().await;

    let make_tx = |amount: u128| abi::pool::Transaction {
        transaction_id: None,
        transaction_type: abi::pool::TransactionType::AddLiquidity,
        from: TestSuite::operator(),
        amount_0_in: Some(Amount::from_tokens(amount)),
        amount_1_in: Some(Amount::from_tokens(amount)),
        amount_0_out: None,
        amount_1_out: None,
        liquidity: Some(Amount::from_tokens(amount)),
        created_at: Timestamp::from(1),
    };

    for expected_id in [1000u32, 1001] {
        let response = suite
            .execute_operation(PoolStateV1Operation::BuildTransaction {
                transaction: make_tx(1),
            })
            .await;
        let PoolStateV1Response::Transaction(transaction) = response else {
            panic!("Unexpected response");
        };
        assert_eq!(transaction.transaction_id, Some(expected_id));
    }
}

#[tokio::test(flavor = "multi_thread")]
async fn unbound_business_app_rejected_for_all_operations() {
    let token = TestSuite::token_0();
    let account = TestSuite::operator();
    let amount = Amount::from_tokens(1);
    let operations = vec![
        PoolStateV1Operation::SetPool {
            pool: TestSuite::pool(),
        },
        PoolStateV1Operation::MintShares { to: account, amount },
        PoolStateV1Operation::BurnShares {
            from: account,
            amount,
        },
        PoolStateV1Operation::CreditClaimable {
            token: Some(token),
            owner: account,
            amount,
        },
        PoolStateV1Operation::DebitClaimable {
            token: Some(token),
            owner: account,
            amount,
        },
        PoolStateV1Operation::ClaimSuccess {
            token: Some(token),
            owner: account,
            amount,
        },
        PoolStateV1Operation::ClaimFail {
            token: Some(token),
            owner: account,
            amount,
        },
        PoolStateV1Operation::SetFeeTo {
            operator: account,
            account,
        },
        PoolStateV1Operation::SetFeeToSetter {
            operator: account,
            account,
        },
        PoolStateV1Operation::BuildTransaction {
            transaction: abi::pool::Transaction {
                transaction_id: None,
                transaction_type: abi::pool::TransactionType::AddLiquidity,
                from: account,
                amount_0_in: Some(amount),
                amount_1_in: Some(amount),
                amount_0_out: None,
                amount_1_out: None,
                liquidity: Some(amount),
                created_at: Timestamp::from(1),
            },
        },
        PoolStateV1Operation::Pool,
        PoolStateV1Operation::RouterApplicationId,
        PoolStateV1Operation::TotalSupply,
        PoolStateV1Operation::Liquidity { account },
        PoolStateV1Operation::ClaimableBalance {
            token: Some(token),
            owner: account,
        },
        PoolStateV1Operation::ClaimingBalance {
            token: Some(token),
            owner: account,
        },
    ];

    for operation in operations {
        let mut suite = TestSuite::new();
        suite.initialize().await;
        suite.set_authenticated_caller(TestSuite::other_business_application_id());

        let response = suite.execute_operation(operation).await;
        assert!(
            matches!(response, PoolStateV1Response::Fail(_)),
            "foreign caller must be rejected"
        );
    }
}

#[tokio::test(flavor = "multi_thread")]
async fn set_pool_updates_pool_record() {
    let mut suite = TestSuite::new();
    suite.initialize().await;

    let mut pool = TestSuite::pool();
    pool.reserve_0 = Amount::from_tokens(100);
    pool.reserve_1 = Amount::from_tokens(200);
    let response = suite
        .execute_operation(PoolStateV1Operation::SetPool { pool: pool.clone() })
        .await;
    assert_eq!(response, PoolStateV1Response::Ok);

    let response = suite.execute_operation(PoolStateV1Operation::Pool).await;
    assert_eq!(response, PoolStateV1Response::Pool(pool));
}

#[tokio::test(flavor = "multi_thread")]
async fn pool_operations_reject_uninitialized_state() {
    let mut suite = TestSuite::new();

    let response = suite
        .execute_operation(PoolStateV1Operation::SetPool {
            pool: TestSuite::pool(),
        })
        .await;
    assert!(matches!(response, PoolStateV1Response::Fail(_)));

    let response = suite.execute_operation(PoolStateV1Operation::Pool).await;
    assert!(matches!(response, PoolStateV1Response::Fail(_)));

    let response = suite
        .execute_operation(PoolStateV1Operation::RouterApplicationId)
        .await;
    assert!(matches!(response, PoolStateV1Response::Fail(_)));
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic(expected = "Invalid amount")]
async fn credit_claimable_rejects_zero_amount() {
    let mut suite = TestSuite::new();
    suite.initialize().await;

    suite
        .execute_operation(PoolStateV1Operation::CreditClaimable {
            token: Some(TestSuite::token_0()),
            owner: TestSuite::operator(),
            amount: Amount::ZERO,
        })
        .await;
}

#[tokio::test(flavor = "multi_thread")]
async fn set_pool_rejects_non_creator_chain() {
    let mut suite = TestSuite::new();
    suite.initialize().await;
    suite.set_chain_id(TestSuite::other_chain_id());
    suite.set_application_creator_chain_id(TestSuite::chain_id());

    let response = suite
        .execute_operation(PoolStateV1Operation::SetPool {
            pool: TestSuite::pool(),
        })
        .await;

    assert!(matches!(response, PoolStateV1Response::Fail(_)));
}
