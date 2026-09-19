use super::super::PoolContract;
use abi::meme::{
    MemeOperation, MemeResponse, TransferFromApplicationReceiptPayload,
    TransferFromApplicationReceiptPurpose,
};
use futures::FutureExt as _;
use abi::pool::state_v1::{PoolStateV1Operation, PoolStateV1Response, StateInstantiationArgument};
use abi::pool::{
    AddLiquidityTransferReceipt, BootstrapPolicy, ClaimTransferReceipt, FundRequest, FundType,
    InstantiationArgument, Pool, PoolAbi, PoolInitializeArgument, PoolMessage, PoolOperation,
    PoolParameters, PoolResponse, SwapTransferReceipt, Transaction, TransactionType,
};
use linera_sdk::{
    bcs,
    linera_base_types::{
        Account, AccountOwner, Amount, ApplicationDescription, ApplicationId, BlockHeight, ChainId,
        ModuleId,
    },
    util::BlockingWait,
    views::View,
    Contract, ContractRuntime,
};
use pool::state::PoolState;
use pool_state::interfaces::state::StateInterface as StateAppInterface;
use pool_state::state::PoolState as StateAppState;
use std::str::FromStr;
use std::{cell::RefCell, rc::Rc};

struct TestSuite {
    contract: PoolContract,
    state_app: Rc<RefCell<StateAppState>>,
}

impl TestSuite {
    fn token_0() -> ApplicationId {
        ApplicationId::from_str(
            "b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bad",
        )
        .unwrap()
    }

    fn token_1() -> ApplicationId {
        ApplicationId::from_str(
            "b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bae",
        )
        .unwrap()
    }

    fn swap_application_id() -> ApplicationId {
        ApplicationId::from_str(
            "b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5baf",
        )
        .unwrap()
    }

    fn state_application_id() -> ApplicationId {
        ApplicationId::from_str(
            "b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bc0",
        )
        .unwrap()
    }

    fn chain_id() -> ChainId {
        ChainId::from_str("aee928d4bf3880353b4a3cd9b6f88e6cc6e5ed050860abae439e7782e9b2dfe8")
            .unwrap()
    }

    fn pool_application_id() -> ApplicationId<PoolAbi> {
        ApplicationId::from_str(
            "b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bbd",
        )
        .unwrap()
        .with_abi::<PoolAbi>()
    }

    fn signer() -> AccountOwner {
        AccountOwner::from_str("0x5279b3ae14d3b38e14b65a74aefe44824ea88b25c7841836e9ec77d991a5bc7f")
            .unwrap()
    }

    fn mock_token_creator_chain_id() -> ChainId {
        ChainId::from_str("a10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5baa")
            .unwrap()
    }

    fn authenticated_account(&self) -> Account {
        Account {
            chain_id: Self::chain_id(),
            owner: Self::signer(),
        }
    }

    async fn execute_operation(&mut self, operation: PoolOperation) -> PoolResponse {
        self.contract.execute_operation(operation).await
    }

    async fn execute_message(&mut self, message: PoolMessage) {
        self.contract.execute_message(message).await;
    }

    fn pool(&self) -> Pool {
        self.state_app
            .borrow_mut()
            .pool()
            .blocking_wait()
            .expect("Failed to read pool from state app")
    }

    fn total_supply(&self) -> Amount {
        self.state_app
            .borrow_mut()
            .total_supply()
            .blocking_wait()
            .expect("Failed to read total supply from state app")
    }

    fn claimable_balance(&self, token: Option<ApplicationId>, owner: Account) -> Amount {
        self.state_app
            .borrow_mut()
            .claimable_balance(token, owner)
            .blocking_wait()
            .expect("Failed to read claimable balance from state app")
    }

    fn claiming_balance(&self, token: Option<ApplicationId>, owner: Account) -> Amount {
        self.state_app
            .borrow_mut()
            .claiming_balance(token, owner)
            .blocking_wait()
            .expect("Failed to read claiming balance from state app")
    }

    fn liquidity(&self, owner: Account) -> Amount {
        self.state_app
            .borrow_mut()
            .liquidity(owner)
            .blocking_wait()
            .expect("Failed to read liquidity from state app")
    }

    fn alternate_account() -> Account {
        Account {
            chain_id: Self::chain_id(),
            owner: AccountOwner::from_str(
                "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            )
            .unwrap(),
        }
    }

    fn configure_fund_result_source(&mut self, token_chain: ChainId, signer: Account) {
        let pool_application_id = TestSuite::pool_application_id().forget_abi();
        let mut runtime = self.contract.runtime.borrow_mut();
        runtime.set_message_origin_chain_id(token_chain);
        runtime.set_authenticated_caller_id(pool_application_id);
        runtime.set_authenticated_signer(Some(signer.owner));
    }

    async fn create_pool(bootstrap_policy: BootstrapPolicy, token_1: Option<ApplicationId>) -> Self {
        let _ = env_logger::builder().is_test(true).try_init();

        let chain_id = Self::chain_id();
        let parameters = PoolParameters {
            creator: Account {
                chain_id,
                owner: Self::signer(),
            },
            token_0: Self::token_0(),
            token_1,
            bootstrap_policy,
        };

        let token_description = ApplicationDescription {
            module_id: ModuleId::default(),
            creator_chain_id: Self::mock_token_creator_chain_id(),
            block_height: BlockHeight(0),
            application_index: 0,
            parameters: vec![],
            required_application_ids: vec![],
        };

        let mut runtime = ContractRuntime::new()
            .with_chain_id(chain_id)
            .with_application_id(Self::pool_application_id())
            .with_application_parameters(parameters)
            .with_authenticated_caller_id(Self::swap_application_id())
            .with_application_description(Self::token_0(), token_description.clone())
            .with_application_description(token_1.unwrap_or_else(Self::token_1), token_description)
            .with_application_creator_chain_id(chain_id)
            .with_system_time(0.into())
            .with_authenticated_signer(Self::signer());
        runtime.set_message_origin_chain_id(chain_id);

        let mut contract = PoolContract {
            state: Rc::new(RefCell::new(
                PoolState::load(runtime.root_view_storage_context())
                    .blocking_wait()
                    .expect("Failed to read from mock key value store"),
            )),
            runtime: Rc::new(RefCell::new(runtime)),
        };

        contract
            .instantiate(InstantiationArgument {
                pool_fee_percent_mul_100: 30,
                router_application_id: Self::swap_application_id(),
                amount_0_in: Amount::ZERO,
                amount_1_in: Amount::ZERO,
            })
            .await;

        // State app behind the mock call_application handler.
        let state_app = Rc::new(RefCell::new(
            StateAppState::load(contract.runtime.borrow_mut().root_view_storage_context())
                .blocking_wait()
                .expect("Failed to load pool state v1"),
        ));
        state_app
            .borrow_mut()
            .instantiate(StateInstantiationArgument {
                business_application_id: Self::pool_application_id().forget_abi(),
                operator: Some(Account {
                    chain_id,
                    owner: Self::signer(),
                }),
            })
            .expect("Failed to instantiate pool state app");

        // Manual append, consistent with meme unit tests.
        contract
            .state
            .borrow_mut()
            .state_applications
            .insert(&1, Self::state_application_id())
            .unwrap();
        contract.state.borrow_mut().latest_state_version.set(1);

        let state_app_for_handler = state_app.clone();
        contract
            .runtime
            .borrow_mut()
            .set_call_application_handler(move |_authenticated, app_id, operation| {
                if app_id == Self::state_application_id() {
                    dispatch_state_operation(&mut state_app_for_handler.borrow_mut(), &operation)
                } else {
                    mock_non_state_application_call(app_id, &operation)
                }
            });

        let mut suite = Self { contract, state_app };

        // Initialize the pool state via the real business Initialize operation.
        suite
            .execute_operation(PoolOperation::Initialize {
                argument: PoolInitializeArgument {
                    router_application_id: Self::swap_application_id(),
                    pool_fee_percent_mul_100: 30,
                },
            })
            .await;

        suite
    }

    async fn create_initialized_pool(
        virtual_initial_liquidity: bool,
        token_1: Option<ApplicationId>,
    ) -> Self {
        let mut suite = Self::create_pool(
            BootstrapPolicy::MemeInitializeLiquidity {
                virtual_initial_liquidity,
            },
            token_1,
        )
        .await;
        let origin = suite.authenticated_account();
        suite
            .execute_message(PoolMessage::InitializeLiquidity {
                origin,
                amount_0_in: Amount::from_tokens(1000),
                amount_1_in: Amount::from_tokens(10),
                to: None,
                block_timestamp: None,
            })
            .await;
        suite
    }
}

fn mock_non_state_application_call(
    _application_id: ApplicationId,
    _operation: &[u8],
) -> Vec<u8> {
    bcs::to_bytes(&PoolStateV1Response::Ok).expect("Failed to serialize mock response")
}

fn dispatch_state_operation(state: &mut StateAppState, operation: &[u8]) -> Vec<u8> {
    let operation =
        bcs::from_bytes::<PoolStateV1Operation>(operation).expect("Failed to deserialize operation");
    let response = match operation {
        PoolStateV1Operation::SetOperator { new_operator } => state
            .set_operator(new_operator)
            .blocking_wait()
            .map(|_| PoolStateV1Response::Ok),
        PoolStateV1Operation::Initialize {
            pool,
            router_application_id,
        } => state
            .initialize(pool, router_application_id)
            .blocking_wait()
            .map(|_| PoolStateV1Response::Ok),
        PoolStateV1Operation::SetPool { pool } => state
            .set_pool(pool)
            .blocking_wait()
            .map(|_| PoolStateV1Response::Ok),
        PoolStateV1Operation::MintShares { to, amount } => state
            .mint_shares(to, amount)
            .blocking_wait()
            .map(|_| PoolStateV1Response::Ok),
        PoolStateV1Operation::BurnShares { from, amount } => state
            .burn_shares(from, amount)
            .blocking_wait()
            .map(|_| PoolStateV1Response::Ok),
        PoolStateV1Operation::CreditClaimable {
            token,
            owner,
            amount,
        } => state
            .credit_claimable(token, owner, amount)
            .blocking_wait()
            .map(|_| PoolStateV1Response::Ok),
        PoolStateV1Operation::DebitClaimable {
            token,
            owner,
            amount,
        } => state
            .debit_claimable(token, owner, amount)
            .blocking_wait()
            .map(|_| PoolStateV1Response::Ok),
        PoolStateV1Operation::Claim {
            token,
            owner,
            amount,
        } => state
            .claim(token, owner, amount)
            .blocking_wait()
            .map(|_| PoolStateV1Response::Ok),
        PoolStateV1Operation::ClaimSuccess {
            token,
            owner,
            amount,
        } => state
            .claim_success(token, owner, amount)
            .blocking_wait()
            .map(|_| PoolStateV1Response::Ok),
        PoolStateV1Operation::ClaimFail {
            token,
            owner,
            amount,
        } => state
            .claim_fail(token, owner, amount)
            .blocking_wait()
            .map(|_| PoolStateV1Response::Ok),
        PoolStateV1Operation::SetFeeTo { operator, account } => state
            .set_fee_to(operator, account)
            .blocking_wait()
            .map(|_| PoolStateV1Response::Ok),
        PoolStateV1Operation::SetFeeToSetter { operator, account } => state
            .set_fee_to_setter(operator, account)
            .blocking_wait()
            .map(|_| PoolStateV1Response::Ok),
        PoolStateV1Operation::BuildTransaction { transaction } => state
            .build_transaction(transaction)
            .blocking_wait()
            .map(PoolStateV1Response::Transaction),
        PoolStateV1Operation::Pool => state.pool().blocking_wait().map(PoolStateV1Response::Pool),
        PoolStateV1Operation::RouterApplicationId => state
            .router_application_id()
            .blocking_wait()
            .map(PoolStateV1Response::RouterApplicationId),
        PoolStateV1Operation::TotalSupply => state
            .total_supply()
            .blocking_wait()
            .map(PoolStateV1Response::TotalSupply),
        PoolStateV1Operation::Liquidity { account } => state
            .liquidity(account)
            .blocking_wait()
            .map(PoolStateV1Response::Liquidity),
        PoolStateV1Operation::ClaimableBalance { token, owner } => state
            .claimable_balance(token, owner)
            .blocking_wait()
            .map(PoolStateV1Response::ClaimableBalance),
        PoolStateV1Operation::ClaimingBalance { token, owner } => state
            .claiming_balance(token, owner)
            .blocking_wait()
            .map(PoolStateV1Response::ClaimingBalance),
        PoolStateV1Operation::Handoff { .. } => {
            panic!("Handoff is not dispatched in unit tests")
        }
    };
    let response = match response {
        Ok(response) => response,
        Err(error) => PoolStateV1Response::Fail(format!("{error}")),
    };
    bcs::to_bytes(&response).expect("Failed to serialize state response")
}

#[tokio::test(flavor = "multi_thread")]
async fn create_pool_with_real_liquidity() {
    let suite = TestSuite::create_pool(
        BootstrapPolicy::MemeInitializeLiquidity {
            virtual_initial_liquidity: false,
        },
        Some(TestSuite::token_1()),
    )
    .await;

    assert_eq!(suite.pool().reserve_0, Amount::ZERO);
    assert_eq!(suite.pool().reserve_1, Amount::ZERO);
    assert_eq!(suite.total_supply(), Amount::ZERO);
}

#[tokio::test(flavor = "multi_thread")]
async fn create_pool_with_virtual_liquidity() {
    let suite = TestSuite::create_pool(
        BootstrapPolicy::MemeInitializeLiquidity {
            virtual_initial_liquidity: true,
        },
        Some(TestSuite::token_1()),
    )
    .await;

    assert_eq!(suite.pool().reserve_0, Amount::ZERO);
    assert_eq!(suite.pool().reserve_1, Amount::ZERO);
    assert_eq!(suite.total_supply(), Amount::ZERO);
}

#[tokio::test(flavor = "multi_thread")]
async fn message_initialize_liquidity_writes_first_reserve_share_facts() {
    let mut suite = TestSuite::create_pool(
        BootstrapPolicy::MemeInitializeLiquidity {
            virtual_initial_liquidity: false,
        },
        Some(TestSuite::token_1()),
    )
    .await;
    let origin = suite.authenticated_account();

    suite
        .execute_message(PoolMessage::InitializeLiquidity {
            origin,
            amount_0_in: Amount::from_tokens(1000),
            amount_1_in: Amount::from_tokens(10),
            to: None,
            block_timestamp: None,
        })
        .await;

    assert_eq!(suite.pool().reserve_0, Amount::from_tokens(1000));
    assert_eq!(suite.pool().reserve_1, Amount::from_tokens(10));
    assert!(suite.total_supply() > Amount::ZERO);
}

#[tokio::test(flavor = "multi_thread")]
async fn virtual_initial_liquidity_does_not_create_claimable_balance() {
    let mut suite = TestSuite::create_pool(
        BootstrapPolicy::MemeInitializeLiquidity {
            virtual_initial_liquidity: true,
        },
        Some(TestSuite::token_1()),
    )
    .await;
    let owner = suite.authenticated_account();

    suite
        .execute_message(PoolMessage::InitializeLiquidity {
            origin: owner,
            amount_0_in: Amount::from_tokens(1000),
            amount_1_in: Amount::from_tokens(10),
            to: None,
            block_timestamp: None,
        })
        .await;

    let other = Account {
        chain_id: TestSuite::chain_id(),
        owner: AccountOwner::from_str(
            "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        )
        .unwrap(),
    };
    for account in [owner, other] {
        assert_eq!(
            suite.claimable_balance(Some(TestSuite::token_0()), account),
            Amount::ZERO
        );
        assert_eq!(
            suite.claimable_balance(Some(TestSuite::token_1()), account),
            Amount::ZERO
        );
        assert_eq!(suite.claimable_balance(None, account), Amount::ZERO);
    }
}

#[tokio::test(flavor = "multi_thread")]
async fn message_initialize_liquidity_rejects_user_create_pool_policy() {
    let mut suite =
        TestSuite::create_pool(BootstrapPolicy::UserCreatePool, Some(TestSuite::token_1())).await;
    let origin = suite.authenticated_account();

    let result = std::panic::AssertUnwindSafe(suite.execute_message(
        PoolMessage::InitializeLiquidity {
            origin,
            amount_0_in: Amount::from_tokens(1000),
            amount_1_in: Amount::from_tokens(10),
            to: None,
            block_timestamp: None,
        },
    ))
    .catch_unwind()
    .await;

    assert!(result.is_err());
    assert_eq!(suite.pool().reserve_0, Amount::ZERO);
    assert_eq!(suite.pool().reserve_1, Amount::ZERO);
    assert_eq!(suite.total_supply(), Amount::ZERO);
}

#[tokio::test(flavor = "multi_thread")]
async fn operation_initialize_liquidity_requires_token0_caller_and_queues_finalize_message() {
    let mut suite = TestSuite::create_pool(
        BootstrapPolicy::MemeInitializeLiquidity {
            virtual_initial_liquidity: false,
        },
        None,
    )
    .await;
    suite
        .contract
        .runtime
        .borrow_mut()
        .set_authenticated_caller_id(TestSuite::token_0());

    let response = suite
        .execute_operation(PoolOperation::InitializeLiquidity {
            amount_0_in: Amount::from_tokens(1000),
            amount_1_in: Amount::from_tokens(10),
            to: None,
            block_timestamp: None,
        })
        .await;

    assert!(matches!(response, PoolResponse::Ok));
    assert_eq!(suite.pool().reserve_0, Amount::ZERO);
    assert_eq!(suite.pool().reserve_1, Amount::ZERO);

    let runtime = suite.contract.runtime.borrow();
    let requests = runtime.created_send_message_requests();
    assert!(requests
        .iter()
        .all(|request| request.authenticated && !request.is_tracked));
    assert_eq!(
        requests
            .iter()
            .filter(|request| matches!(request.message, PoolMessage::InitializeLiquidity { .. }))
            .count(),
        1
    );
}

#[tokio::test(flavor = "multi_thread")]
async fn operation_initialize_liquidity_rejects_non_token0_caller() {
    let mut suite = TestSuite::create_pool(
        BootstrapPolicy::MemeInitializeLiquidity {
            virtual_initial_liquidity: false,
        },
        None,
    )
    .await;

    let result = std::panic::AssertUnwindSafe(suite.execute_operation(
        PoolOperation::InitializeLiquidity {
            amount_0_in: Amount::from_tokens(1000),
            amount_1_in: Amount::from_tokens(10),
            to: None,
            block_timestamp: None,
        },
    ))
    .catch_unwind()
    .await;

    assert!(result.is_err());
}

#[tokio::test(flavor = "multi_thread")]
async fn operation_swap() {
    let mut suite = TestSuite::create_initialized_pool(true, Some(TestSuite::token_1())).await;

    let response = suite
        .execute_operation(PoolOperation::Swap {
            amount_0_in: None,
            amount_1_in: Some(Amount::ONE),
            amount_0_out_min: None,
            amount_1_out_min: None,
            to: None,
            block_timestamp: None,
        })
        .now_or_never()
        .expect("Execution of pool operation should not await anything");

    assert!(matches!(response, PoolResponse::Ok));
}

#[tokio::test(flavor = "multi_thread")]
async fn operation_swap_meme_input_queues_message_carried_funding_without_persisting_request() {
    let mut suite = TestSuite::create_initialized_pool(true, Some(TestSuite::token_1())).await;
    let origin = suite.authenticated_account();
    let token_chain = TestSuite::mock_token_creator_chain_id();
    let message_count_before = suite
        .contract
        .runtime
        .borrow()
        .created_send_message_requests()
        .len();

    let response = suite
        .execute_operation(PoolOperation::Swap {
            amount_0_in: Some(Amount::ONE),
            amount_1_in: None,
            amount_0_out_min: None,
            amount_1_out_min: Some(Amount::from_attos(1)),
            to: None,
            block_timestamp: None,
        })
        .await;

    assert!(matches!(response, PoolResponse::Ok));
    let runtime = suite.contract.runtime.borrow();
    let requests = &runtime.created_send_message_requests()[message_count_before..];
    assert_eq!(requests.len(), 1);
    assert_eq!(requests[0].destination, token_chain);
    assert!(requests[0].authenticated);
    assert!(!requests[0].is_tracked);
    assert!(matches!(
        &requests[0].message,
        PoolMessage::RequestFund {
            prev: None,
            request,
            next: None,
        } if request.from == origin
        && request.token == Some(TestSuite::token_0())
        && request.amount_in == Amount::ONE
        && request.counterparty_amount_out_min == Some(Amount::from_attos(1))
        && request.fund_type == FundType::Swap
    ));
}

#[tokio::test(flavor = "multi_thread")]
async fn message_swap_rejects_without_finalized_reserve_share_facts() {
    let mut suite = TestSuite::create_pool(
        BootstrapPolicy::MemeInitializeLiquidity {
            virtual_initial_liquidity: false,
        },
        Some(TestSuite::token_1()),
    )
    .await;
    let origin = suite.authenticated_account();
    let reserve_0_before = suite.pool().reserve_0;
    let reserve_1_before = suite.pool().reserve_1;
    let total_supply_before = suite.total_supply();
    let request_count_before = suite
        .contract
        .runtime
        .borrow()
        .created_send_message_requests()
        .len();

    suite
        .execute_message(PoolMessage::Swap {
            origin,
            amount_0_in: Some(Amount::ONE),
            amount_1_in: None,
            amount_0_out_min: None,
            amount_1_out_min: None,
            to: None,
            block_timestamp: None,
        })
        .await;

    assert_eq!(
        suite.claimable_balance(Some(TestSuite::token_0()), origin),
        Amount::ONE
    );
    assert_eq!(suite.pool().reserve_0, reserve_0_before);
    assert_eq!(suite.pool().reserve_1, reserve_1_before);
    assert_eq!(suite.total_supply(), total_supply_before);
    assert_eq!(
        suite
            .contract
            .runtime
            .borrow()
            .created_send_message_requests()
            .len(),
        request_count_before
    );
}

#[tokio::test(flavor = "multi_thread")]
async fn operation_add_liquidity() {
    let mut suite = TestSuite::create_pool(
        BootstrapPolicy::MemeInitializeLiquidity {
            virtual_initial_liquidity: true,
        },
        Some(TestSuite::token_1()),
    )
    .await;

    let response = suite
        .execute_operation(PoolOperation::AddLiquidity {
            amount_0_in: Amount::ONE,
            amount_1_in: Amount::from_tokens(20),
            amount_0_out_min: None,
            amount_1_out_min: None,
            to: None,
            block_timestamp: None,
        })
        .now_or_never()
        .expect("Execution of pool operation should not await anything");

    assert!(matches!(response, PoolResponse::Ok));
}

#[tokio::test(flavor = "multi_thread")]
async fn message_remove_liquidity_rejects_without_finalized_reserve_share_facts() {
    let mut suite = TestSuite::create_pool(
        BootstrapPolicy::MemeInitializeLiquidity {
            virtual_initial_liquidity: false,
        },
        Some(TestSuite::token_1()),
    )
    .await;
    let origin = suite.authenticated_account();
    let reserve_0_before = suite.pool().reserve_0;
    let reserve_1_before = suite.pool().reserve_1;
    let total_supply_before = suite.total_supply();
    let request_count_before = suite
        .contract
        .runtime
        .borrow()
        .created_send_message_requests()
        .len();

    let result = std::panic::AssertUnwindSafe(suite.execute_message(
        PoolMessage::RemoveLiquidity {
            origin,
            liquidity: Amount::ONE,
            amount_0_out_min: None,
            amount_1_out_min: None,
            to: None,
            block_timestamp: None,
        },
    ))
    .catch_unwind()
    .await;

    assert!(result.is_err());
    assert_eq!(suite.pool().reserve_0, reserve_0_before);
    assert_eq!(suite.pool().reserve_1, reserve_1_before);
    assert_eq!(suite.total_supply(), total_supply_before);
    assert_eq!(
        suite
            .contract
            .runtime
            .borrow()
            .created_send_message_requests()
            .len(),
        request_count_before
    );
}

#[tokio::test(flavor = "multi_thread")]
async fn message_set_fee_to_updates_fee_receiver_for_current_fee_to_setter() {
    let mut suite = TestSuite::create_pool(
        BootstrapPolicy::MemeInitializeLiquidity {
            virtual_initial_liquidity: true,
        },
        Some(TestSuite::token_1()),
    )
    .await;
    let operator = suite.authenticated_account();
    let account = Account {
        chain_id: operator.chain_id,
        owner: AccountOwner::from_str(
            "0x8b0f4d4320f64d5cf5fd742f5a7d6a51a8c3dbd9d6c6c23f73e3b0f8fbb04f11",
        )
        .unwrap(),
    };

    suite
        .execute_message(PoolMessage::SetFeeTo { operator, account })
        .await;

    let pool = suite.pool();
    assert_eq!(pool.fee_to, account);
    assert_eq!(pool.fee_to_setter, operator);
}

#[tokio::test(flavor = "multi_thread")]
async fn message_set_fee_to_setter_rotates_operator_and_invalidates_old_operator() {
    let mut suite = TestSuite::create_pool(
        BootstrapPolicy::MemeInitializeLiquidity {
            virtual_initial_liquidity: true,
        },
        Some(TestSuite::token_1()),
    )
    .await;
    let old_operator = suite.authenticated_account();
    let new_operator = Account {
        chain_id: old_operator.chain_id,
        owner: AccountOwner::from_str(
            "0x3f3c6f7fbc833f18d48f3b9d8552cf16e491061b85d34ed2a5b3720d9f2f4c31",
        )
        .unwrap(),
    };
    let target_fee_to = Account {
        chain_id: old_operator.chain_id,
        owner: AccountOwner::from_str(
            "0x3447565f8a4f3db39c46fc92f6fa5700d6c74a585cd49007daa4619052f5e91b",
        )
        .unwrap(),
    };

    suite
        .execute_message(PoolMessage::SetFeeToSetter {
            operator: old_operator,
            account: new_operator,
        })
        .await;
    assert_eq!(suite.pool().fee_to_setter, new_operator);

    let old_operator_attempt = std::panic::AssertUnwindSafe(suite.execute_message(
        PoolMessage::SetFeeTo {
            operator: old_operator,
            account: target_fee_to,
        },
    ))
    .catch_unwind()
    .await;
    assert!(old_operator_attempt.is_err());

    suite
        .execute_message(PoolMessage::SetFeeTo {
            operator: new_operator,
            account: target_fee_to,
        })
        .await;

    let pool = suite.pool();
    assert_eq!(pool.fee_to_setter, new_operator);
    assert_eq!(pool.fee_to, target_fee_to);
}

#[tokio::test(flavor = "multi_thread")]
async fn message_set_fee_to_rejects_non_operator() {
    let mut suite = TestSuite::create_pool(
        BootstrapPolicy::MemeInitializeLiquidity {
            virtual_initial_liquidity: true,
        },
        Some(TestSuite::token_1()),
    )
    .await;
    let current_operator = suite.authenticated_account();
    let invalid_operator = Account {
        chain_id: current_operator.chain_id,
        owner: AccountOwner::from_str(
            "0x61f6a31f937dfb8a5e47f6d471b1e40f949e8ddfb66914318e403d315f0dce21",
        )
        .unwrap(),
    };
    let target_fee_to = Account {
        chain_id: current_operator.chain_id,
        owner: AccountOwner::from_str(
            "0x216bd78c27e4abfef4e1a6b4af2f14f4dd35df621d8f21891cf9d33d6535f1a1",
        )
        .unwrap(),
    };

    let result = std::panic::AssertUnwindSafe(suite.execute_message(
        PoolMessage::SetFeeTo {
            operator: invalid_operator,
            account: target_fee_to,
        },
    ))
    .catch_unwind()
    .await;

    assert!(result.is_err());
    let pool = suite.pool();
    assert_eq!(pool.fee_to_setter, current_operator);
    assert_eq!(pool.fee_to, current_operator);
}

#[tokio::test(flavor = "multi_thread")]
async fn message_swap() {
    let mut suite = TestSuite::create_initialized_pool(true, Some(TestSuite::token_1())).await;
    let owner = suite.authenticated_account();

    let reserve_0 = suite.pool().reserve_0;
    let reserve_1 = suite.pool().reserve_1;
    let swap_amount_0 = suite.pool().calculate_swap_amount_0(Amount::ONE).unwrap();

    suite
        .execute_message(PoolMessage::Swap {
            origin: owner,
            amount_0_in: None,
            amount_1_in: Some(Amount::ONE),
            amount_0_out_min: None,
            amount_1_out_min: None,
            to: None,
            block_timestamp: None,
        })
        .await;

    assert_eq!(reserve_0.try_sub(swap_amount_0).unwrap(), suite.pool().reserve_0);
    assert_eq!(reserve_1.try_add(Amount::ONE).unwrap(), suite.pool().reserve_1);
    assert_eq!(
        suite.claimable_balance(Some(TestSuite::token_0()), owner),
        swap_amount_0
    );
}

#[tokio::test(flavor = "multi_thread")]
async fn message_swap_min_amount_boundary() {
    let mut suite = TestSuite::create_initialized_pool(true, Some(TestSuite::token_1())).await;
    let owner = suite.authenticated_account();
    let amount_1_in = Amount::ONE;
    let exact_amount_0_out = suite.pool().calculate_swap_amount_0(amount_1_in).unwrap();

    suite
        .execute_message(PoolMessage::Swap {
            origin: owner,
            amount_0_in: None,
            amount_1_in: Some(amount_1_in),
            amount_0_out_min: Some(exact_amount_0_out),
            amount_1_out_min: None,
            to: None,
            block_timestamp: None,
        })
        .await;

    let mut suite = TestSuite::create_initialized_pool(true, Some(TestSuite::token_1())).await;
    let owner = suite.authenticated_account();
    let reserve_0 = suite.pool().reserve_0;
    let reserve_1 = suite.pool().reserve_1;
    suite
        .execute_message(PoolMessage::Swap {
            origin: owner,
            amount_0_in: None,
            amount_1_in: Some(amount_1_in),
            amount_0_out_min: Some(exact_amount_0_out.try_add(Amount::from_attos(1)).unwrap()),
            amount_1_out_min: None,
            to: None,
            block_timestamp: None,
        })
        .await;
    assert_eq!(suite.pool().reserve_0, reserve_0);
    assert_eq!(suite.pool().reserve_1, reserve_1);
}

#[tokio::test(flavor = "multi_thread")]
async fn message_add_liquidity() {
    let mut suite = TestSuite::create_initialized_pool(true, Some(TestSuite::token_1())).await;
    let owner = suite.authenticated_account();

    suite
        .execute_message(PoolMessage::AddLiquidity {
            origin: owner,
            amount_0_in: Amount::ONE,
            amount_1_in: Amount::from_tokens(10),
            amount_0_out_min: None,
            amount_1_out_min: None,
            to: None,
            block_timestamp: None,
        })
        .await;

    assert_eq!(suite.liquidity(owner), Amount::from_str("100.1").unwrap());

    let (amount_0_out, amount_1_out) = suite
        .pool()
        .try_calculate_liquidity_amount_pair(
            Amount::from_str("100.05").unwrap(),
            suite.total_supply(),
            None,
            None,
        )
        .unwrap();
    let claimable_0_before = suite.claimable_balance(Some(TestSuite::token_0()), owner);
    let claimable_1_before = suite.claimable_balance(Some(TestSuite::token_1()), owner);

    suite
        .execute_message(PoolMessage::RemoveLiquidity {
            origin: owner,
            liquidity: Amount::from_str("100.05").unwrap(),
            amount_0_out_min: None,
            amount_1_out_min: None,
            to: None,
            block_timestamp: None,
        })
        .await;

    assert_eq!(suite.liquidity(owner), Amount::from_str("0.05").unwrap());

    assert!(amount_0_out > Amount::ZERO);
    assert!(amount_1_out > Amount::ZERO);
    assert_eq!(
        suite.claimable_balance(Some(TestSuite::token_0()), owner),
        claimable_0_before.try_add(amount_0_out).unwrap()
    );
    assert_eq!(
        suite.claimable_balance(Some(TestSuite::token_1()), owner),
        claimable_1_before.try_add(amount_1_out).unwrap()
    );
}

#[tokio::test(flavor = "multi_thread")]
async fn message_remove_liquidity_native_output_claims_through_claim_path() {
    let mut suite = TestSuite::create_initialized_pool(false, None).await;
    let owner = suite.authenticated_account();

    let liquidity = Amount::from_str("10").unwrap();
    let (amount_0_out, amount_1_out) = suite
        .pool()
        .try_calculate_liquidity_amount_pair(liquidity, suite.total_supply(), None, None)
        .unwrap();
    let application_owner = AccountOwner::from(TestSuite::pool_application_id().forget_abi());

    suite
        .contract
        .runtime
        .borrow_mut()
        .set_owner_balance(application_owner, amount_1_out);
    suite
        .contract
        .runtime
        .borrow_mut()
        .set_owner_balance(owner.owner, Amount::ZERO);

    suite
        .execute_message(PoolMessage::RemoveLiquidity {
            origin: owner,
            liquidity,
            amount_0_out_min: None,
            amount_1_out_min: None,
            to: None,
            block_timestamp: None,
        })
        .await;

    assert_eq!(
        suite.claimable_balance(Some(TestSuite::token_0()), owner),
        amount_0_out
    );
    assert_eq!(suite.claimable_balance(None, owner), amount_1_out);

    suite
        .execute_message(PoolMessage::Claim {
            origin: owner,
            token: None,
            amount: amount_1_out,
        })
        .await;

    assert_eq!(suite.claimable_balance(None, owner), Amount::ZERO);
    assert_eq!(
        suite.contract.runtime.borrow_mut().owner_balance(owner.owner),
        amount_1_out
    );
}

#[tokio::test(flavor = "multi_thread")]
async fn message_add_liquidity_min_amount_boundary() {
    let mut suite = TestSuite::create_initialized_pool(true, Some(TestSuite::token_1())).await;
    let owner = suite.authenticated_account();
    let amount_0_in = Amount::ONE;
    let amount_1_in = Amount::ONE;
    let (_, exact_amount_1) = suite
        .pool()
        .try_calculate_swap_amount_pair(amount_0_in, amount_1_in, None, None)
        .unwrap();

    suite
        .execute_message(PoolMessage::AddLiquidity {
            origin: owner,
            amount_0_in,
            amount_1_in,
            amount_0_out_min: None,
            amount_1_out_min: Some(exact_amount_1),
            to: None,
            block_timestamp: None,
        })
        .await;

    let mut suite = TestSuite::create_initialized_pool(true, Some(TestSuite::token_1())).await;
    let owner = suite.authenticated_account();
    suite
        .execute_message(PoolMessage::AddLiquidity {
            origin: owner,
            amount_0_in,
            amount_1_in,
            amount_0_out_min: None,
            amount_1_out_min: Some(exact_amount_1.try_add(Amount::from_attos(1)).unwrap()),
            to: None,
            block_timestamp: None,
        })
        .await;
    assert_eq!(
        suite.claimable_balance(Some(TestSuite::token_0()), owner),
        amount_0_in
    );
    assert_eq!(
        suite.claimable_balance(Some(TestSuite::token_1()), owner),
        amount_1_in
    );
}

#[tokio::test(flavor = "multi_thread")]
async fn message_remove_liquidity_min_amount_boundary() {
    let liquidity = Amount::from_str("0.05").unwrap();

    let mut suite = TestSuite::create_initialized_pool(true, Some(TestSuite::token_1())).await;
    let owner = suite.authenticated_account();
    suite
        .execute_message(PoolMessage::AddLiquidity {
            origin: owner,
            amount_0_in: Amount::ONE,
            amount_1_in: Amount::from_tokens(10),
            amount_0_out_min: None,
            amount_1_out_min: None,
            to: None,
            block_timestamp: None,
        })
        .await;
    let (exact_amount_0, exact_amount_1) = suite
        .pool()
        .try_calculate_liquidity_amount_pair(liquidity, suite.total_supply(), None, None)
        .unwrap();

    suite
        .execute_message(PoolMessage::RemoveLiquidity {
            origin: owner,
            liquidity,
            amount_0_out_min: Some(exact_amount_0),
            amount_1_out_min: Some(exact_amount_1),
            to: None,
            block_timestamp: None,
        })
        .await;

    let mut suite = TestSuite::create_initialized_pool(true, Some(TestSuite::token_1())).await;
    let owner = suite.authenticated_account();
    suite
        .execute_message(PoolMessage::AddLiquidity {
            origin: owner,
            amount_0_in: Amount::ONE,
            amount_1_in: Amount::from_tokens(10),
            amount_0_out_min: None,
            amount_1_out_min: None,
            to: None,
            block_timestamp: None,
        })
        .await;
    let reserve_0_before = suite.pool().reserve_0;
    let reserve_1_before = suite.pool().reserve_1;
    let liquidity_before = suite.liquidity(owner);
    let total_supply_before = suite.total_supply();
    let message_count_before = suite
        .contract
        .runtime
        .borrow()
        .created_send_message_requests()
        .len();
    let claimable_0_before = suite.claimable_balance(Some(TestSuite::token_0()), owner);
    let claimable_1_before = suite.claimable_balance(Some(TestSuite::token_1()), owner);
    let failing_result = std::panic::AssertUnwindSafe(suite.execute_message(
        PoolMessage::RemoveLiquidity {
            origin: owner,
            liquidity,
            amount_0_out_min: Some(exact_amount_0.try_add(Amount::from_attos(1)).unwrap()),
            amount_1_out_min: Some(exact_amount_1),
            to: None,
            block_timestamp: None,
        },
    ))
    .catch_unwind()
    .await;
    assert!(failing_result.is_err());
    assert_eq!(suite.pool().reserve_0, reserve_0_before);
    assert_eq!(suite.pool().reserve_1, reserve_1_before);
    assert_eq!(suite.liquidity(owner), liquidity_before);
    assert_eq!(
        suite.claimable_balance(Some(TestSuite::token_0()), owner),
        claimable_0_before
    );
    assert_eq!(
        suite.claimable_balance(Some(TestSuite::token_1()), owner),
        claimable_1_before
    );
    assert_eq!(suite.total_supply(), total_supply_before);
    let runtime = suite.contract.runtime.borrow();
    assert!(
        runtime.created_send_message_requests()[message_count_before..]
            .iter()
            .all(|message| !matches!(message.message, PoolMessage::NewTransaction { .. }))
    );
}

#[tokio::test(flavor = "multi_thread")]
async fn message_add_liquidity_mints_fee_to_after_swap_growth() {
    let mut suite = TestSuite::create_initialized_pool(false, Some(TestSuite::token_1())).await;
    let operator = suite.authenticated_account();
    let fee_to = TestSuite::alternate_account();

    suite
        .execute_message(PoolMessage::SetFeeTo {
            operator,
            account: fee_to,
        })
        .await;

    suite
        .execute_message(PoolMessage::Swap {
            origin: operator,
            amount_0_in: None,
            amount_1_in: Some(Amount::ONE),
            amount_0_out_min: None,
            amount_1_out_min: None,
            to: None,
            block_timestamp: None,
        })
        .await;

    assert_eq!(suite.liquidity(fee_to), Amount::ZERO);

    suite
        .execute_message(PoolMessage::AddLiquidity {
            origin: operator,
            amount_0_in: Amount::ONE,
            amount_1_in: Amount::from_tokens(10),
            amount_0_out_min: None,
            amount_1_out_min: None,
            to: None,
            block_timestamp: None,
        })
        .await;

    assert!(suite.liquidity(fee_to) > Amount::ZERO);
}

#[tokio::test(flavor = "multi_thread")]
async fn message_remove_liquidity_mints_fee_to_and_updates_reserves_after_swap_growth() {
    let mut suite = TestSuite::create_initialized_pool(false, Some(TestSuite::token_1())).await;
    let operator = suite.authenticated_account();
    let fee_to = TestSuite::alternate_account();

    suite
        .execute_message(PoolMessage::SetFeeTo {
            operator,
            account: fee_to,
        })
        .await;

    suite
        .execute_message(PoolMessage::Swap {
            origin: operator,
            amount_0_in: None,
            amount_1_in: Some(Amount::ONE),
            amount_0_out_min: None,
            amount_1_out_min: None,
            to: None,
            block_timestamp: None,
        })
        .await;

    let reserve_0_before = suite.pool().reserve_0;
    let reserve_1_before = suite.pool().reserve_1;

    suite
        .execute_message(PoolMessage::RemoveLiquidity {
            origin: operator,
            liquidity: Amount::ONE,
            amount_0_out_min: None,
            amount_1_out_min: None,
            to: None,
            block_timestamp: None,
        })
        .await;

    let fee_to_share = suite.liquidity(fee_to);
    assert!(fee_to_share > Amount::ZERO);
    assert!(suite.pool().reserve_0 < reserve_0_before);
    assert!(suite.pool().reserve_1 < reserve_1_before);

    let (fee_to_amount_0, fee_to_amount_1) = suite
        .pool()
        .try_calculate_liquidity_amount_pair(fee_to_share, suite.total_supply(), None, None)
        .unwrap();

    suite
        .execute_message(PoolMessage::RemoveLiquidity {
            origin: fee_to,
            liquidity: fee_to_share,
            amount_0_out_min: None,
            amount_1_out_min: None,
            to: None,
            block_timestamp: None,
        })
        .await;

    assert_eq!(suite.liquidity(fee_to), Amount::ZERO);
    assert_eq!(
        suite.claimable_balance(Some(TestSuite::token_0()), fee_to),
        fee_to_amount_0
    );
    assert_eq!(
        suite.claimable_balance(Some(TestSuite::token_1()), fee_to),
        fee_to_amount_1
    );
}

#[tokio::test(flavor = "multi_thread")]
async fn message_add_liquidity_conserves_total_supply_with_fee_dilution() {
    let mut suite = TestSuite::create_initialized_pool(false, Some(TestSuite::token_1())).await;
    let operator = suite.authenticated_account();
    let fee_to = TestSuite::alternate_account();

    suite
        .execute_message(PoolMessage::SetFeeTo {
            operator,
            account: fee_to,
        })
        .await;

    suite
        .execute_message(PoolMessage::Swap {
            origin: operator,
            amount_0_in: None,
            amount_1_in: Some(Amount::ONE),
            amount_0_out_min: None,
            amount_1_out_min: None,
            to: None,
            block_timestamp: None,
        })
        .await;

    suite
        .execute_message(PoolMessage::AddLiquidity {
            origin: operator,
            amount_0_in: Amount::ONE,
            amount_1_in: Amount::from_tokens(10),
            amount_0_out_min: None,
            amount_1_out_min: None,
            to: None,
            block_timestamp: None,
        })
        .await;

    let fee_to_share = suite.liquidity(fee_to);
    let operator_share = suite.liquidity(operator);
    let total_supply = suite.total_supply();

    assert_eq!(
        fee_to_share,
        Amount::from_str("0.002272933913650825").unwrap()
    );
    assert_eq!(
        operator_share,
        Amount::from_str("100.109972499545424841").unwrap(),
    );
    assert_eq!(
        total_supply,
        Amount::from_str("100.112245433459075666").unwrap()
    );
    assert_eq!(operator_share.try_add(fee_to_share).unwrap(), total_supply);
}

#[tokio::test(flavor = "multi_thread")]
async fn message_remove_liquidity_conserves_total_supply_after_fee_mint() {
    let mut suite = TestSuite::create_initialized_pool(false, Some(TestSuite::token_1())).await;
    let operator = suite.authenticated_account();
    let fee_to = TestSuite::alternate_account();

    suite
        .execute_message(PoolMessage::SetFeeTo {
            operator,
            account: fee_to,
        })
        .await;

    suite
        .execute_message(PoolMessage::Swap {
            origin: operator,
            amount_0_in: None,
            amount_1_in: Some(Amount::ONE),
            amount_0_out_min: None,
            amount_1_out_min: None,
            to: None,
            block_timestamp: None,
        })
        .await;

    suite
        .execute_message(PoolMessage::RemoveLiquidity {
            origin: operator,
            liquidity: Amount::ONE,
            amount_0_out_min: None,
            amount_1_out_min: None,
            to: None,
            block_timestamp: None,
        })
        .await;

    let fee_to_share = suite.liquidity(fee_to);
    let operator_share = suite.liquidity(operator);
    let total_supply = suite.total_supply();

    assert_eq!(
        fee_to_share,
        Amount::from_str("0.002272933913650825").unwrap()
    );
    assert_eq!(operator_share, Amount::from_str("99").unwrap());
    assert_eq!(
        total_supply,
        Amount::from_str("99.002272933913650825").unwrap()
    );
    assert_eq!(operator_share.try_add(fee_to_share).unwrap(), total_supply);
}

#[tokio::test(flavor = "multi_thread")]
async fn message_new_transaction_forwards_catalog_update_without_history_storage() {
    let mut suite = TestSuite::create_initialized_pool(true, Some(TestSuite::token_1())).await;
    let owner = suite.authenticated_account();
    let transaction = suite
        .state_app
        .borrow_mut()
        .build_transaction(Transaction {
            transaction_id: None,
            transaction_type: TransactionType::SellToken0,
            from: owner,
            amount_0_in: Some(Amount::ONE),
            amount_0_out: None,
            amount_1_in: None,
            amount_1_out: Some(Amount::from_str("0.00997").unwrap()),
            liquidity: None,
            created_at: 1.into(),
        })
        .blocking_wait()
        .expect("Failed to assign transaction id");

    suite
        .execute_message(PoolMessage::NewTransaction {
            transaction: transaction.clone(),
        })
        .await;
    suite
        .execute_message(PoolMessage::NewTransaction { transaction })
        .await;

    assert_eq!(transaction.transaction_id, Some(1001));
}

#[tokio::test(flavor = "multi_thread")]
async fn operation_claim_forwards_to_pool_creator_chain_without_state_change() {
    let mut suite = TestSuite::create_pool(
        BootstrapPolicy::MemeInitializeLiquidity {
            virtual_initial_liquidity: false,
        },
        None,
    )
    .await;
    let owner = suite.authenticated_account();
    let user_chain_id =
        ChainId::from_str("bee928d4bf3880353b4a3cd9b6f88e6cc6e5ed050860abae439e7782e9b2dfe8")
            .unwrap();
    let creator_chain_id = suite
        .contract
        .runtime
        .borrow_mut()
        .application_creator_chain_id();
    let amount = Amount::from_tokens(5);
    let creator_account = Account {
        chain_id: creator_chain_id,
        owner: owner.owner,
    };

    suite
        .contract
        .runtime
        .borrow_mut()
        .set_chain_id(user_chain_id);
    suite
        .state_app
        .borrow_mut()
        .credit_claimable(None, creator_account, amount)
        .blocking_wait()
        .expect("Failed to credit claimable balance");

    let response = suite
        .execute_operation(PoolOperation::Claim {
            token: None,
            amount,
        })
        .await;

    assert!(matches!(response, PoolResponse::Ok));
    assert_eq!(suite.claimable_balance(None, creator_account), amount);
    assert_eq!(suite.claiming_balance(None, creator_account), Amount::ZERO);

    let runtime = suite.contract.runtime.borrow();
    let requests = runtime.created_send_message_requests();
    let request = requests.last().unwrap();
    assert_eq!(request.destination, creator_chain_id);
    assert!(request.authenticated);
    assert!(!request.is_tracked);
    assert!(matches!(
        &request.message,
        PoolMessage::Claim { origin, token, amount: claim_amount }
            if origin.chain_id == user_chain_id
                && origin.owner == owner.owner
                && token.is_none()
                && *claim_amount == amount
    ));
}

#[tokio::test(flavor = "multi_thread")]
async fn message_claim_native_transfers_and_completes_claiming() {
    let mut suite = TestSuite::create_pool(
        BootstrapPolicy::MemeInitializeLiquidity {
            virtual_initial_liquidity: false,
        },
        None,
    )
    .await;
    let owner = suite.authenticated_account();
    let amount = Amount::from_tokens(5);
    let application_owner = AccountOwner::from(TestSuite::pool_application_id().forget_abi());

    suite
        .contract
        .runtime
        .borrow_mut()
        .set_owner_balance(application_owner, amount);
    suite
        .contract
        .runtime
        .borrow_mut()
        .set_owner_balance(owner.owner, Amount::ZERO);
    suite
        .state_app
        .borrow_mut()
        .credit_claimable(None, owner, amount)
        .blocking_wait()
        .expect("Failed to credit claimable balance");

    suite
        .execute_message(PoolMessage::Claim {
            origin: owner,
            token: None,
            amount,
        })
        .await;

    assert_eq!(suite.claimable_balance(None, owner), Amount::ZERO);
    assert_eq!(suite.claiming_balance(None, owner), Amount::ZERO);
    assert_eq!(
        suite.contract.runtime.borrow_mut().owner_balance(owner.owner),
        amount
    );
}

#[tokio::test(flavor = "multi_thread")]
async fn message_claim_fungible_moves_to_claiming() {
    let mut suite = TestSuite::create_pool(
        BootstrapPolicy::MemeInitializeLiquidity {
            virtual_initial_liquidity: false,
        },
        Some(TestSuite::token_1()),
    )
    .await;
    let owner = suite.authenticated_account();
    let token_0 = TestSuite::token_0();
    let amount = Amount::from_tokens(5);

    suite
        .state_app
        .borrow_mut()
        .credit_claimable(Some(token_0), owner, amount)
        .blocking_wait()
        .expect("Failed to credit claimable balance");

    let captured = std::rc::Rc::new(std::cell::RefCell::new(None));
    let captured_for_handler = captured.clone();
    let state_app = suite.state_app.clone();
    suite
        .contract
        .runtime
        .borrow_mut()
        .set_call_application_handler(move |_authenticated, application_id, operation| {
            if application_id == TestSuite::state_application_id() {
                dispatch_state_operation(&mut state_app.borrow_mut(), &operation)
            } else {
                *captured_for_handler.borrow_mut() = Some((application_id, operation));
                bcs::to_bytes(&MemeResponse::Ok).expect("Failed to serialize mock response")
            }
        });

    suite
        .execute_message(PoolMessage::Claim {
            origin: owner,
            token: Some(token_0),
            amount,
        })
        .await;

    let (application_id, operation) = captured.borrow().clone().unwrap();
    assert_eq!(application_id, token_0);
    assert!(matches!(
        bcs::from_bytes::<MemeOperation>(&operation).unwrap(),
        MemeOperation::TransferFromApplicationWithReceipt {
            to,
            amount: call_amount,
            receipt,
        } if to == owner
        && call_amount == amount
        && receipt.purpose == TransferFromApplicationReceiptPurpose::PoolClaim
        && receipt.owner == owner
        && receipt.token == token_0
        && receipt.amount == amount
        && receipt.result.is_none()
    ));
    assert_eq!(suite.claimable_balance(Some(token_0), owner), Amount::ZERO);
    assert_eq!(suite.claiming_balance(Some(token_0), owner), amount);
}

#[tokio::test(flavor = "multi_thread")]
async fn message_claim_fungible_pending_amount_cannot_be_claimed_again() {
    let mut suite = TestSuite::create_pool(
        BootstrapPolicy::MemeInitializeLiquidity {
            virtual_initial_liquidity: false,
        },
        Some(TestSuite::token_1()),
    )
    .await;
    let owner = suite.authenticated_account();
    let token_0 = TestSuite::token_0();
    let amount = Amount::from_tokens(5);

    suite
        .state_app
        .borrow_mut()
        .credit_claimable(Some(token_0), owner, amount)
        .blocking_wait()
        .expect("Failed to credit claimable balance");
    suite
        .execute_message(PoolMessage::Claim {
            origin: owner,
            token: Some(token_0),
            amount,
        })
        .await;

    let result = std::panic::AssertUnwindSafe(suite.execute_message(PoolMessage::Claim {
        origin: owner,
        token: Some(token_0),
        amount,
    }))
    .catch_unwind()
    .await;

    assert!(result.is_err());
    assert_eq!(suite.claimable_balance(Some(token_0), owner), Amount::ZERO);
    assert_eq!(suite.claiming_balance(Some(token_0), owner), amount);
}

#[tokio::test(flavor = "multi_thread")]
async fn message_claim_fungible_keeps_claimable_and_claiming_exclusive() {
    let mut suite = TestSuite::create_pool(
        BootstrapPolicy::MemeInitializeLiquidity {
            virtual_initial_liquidity: false,
        },
        Some(TestSuite::token_1()),
    )
    .await;
    let owner = suite.authenticated_account();
    let token_0 = TestSuite::token_0();
    let amount = Amount::from_tokens(5);

    suite
        .contract
        .runtime
        .borrow_mut()
        .set_authenticated_caller_id(token_0);
    suite
        .state_app
        .borrow_mut()
        .credit_claimable(Some(token_0), owner, amount)
        .blocking_wait()
        .expect("Failed to credit claimable balance");

    suite
        .execute_message(PoolMessage::Claim {
            origin: owner,
            token: Some(token_0),
            amount,
        })
        .await;
    assert_eq!(suite.claimable_balance(Some(token_0), owner), Amount::ZERO);
    assert_eq!(suite.claiming_balance(Some(token_0), owner), amount);

    suite
        .execute_message(PoolMessage::ClaimTransferReceipt {
            receipt: ClaimTransferReceipt {
                owner,
                token: token_0,
                amount,
                result: Err("transfer failed".to_string()),
            },
        })
        .await;
    assert_eq!(suite.claimable_balance(Some(token_0), owner), amount);
    assert_eq!(suite.claiming_balance(Some(token_0), owner), Amount::ZERO);

    suite
        .execute_message(PoolMessage::Claim {
            origin: owner,
            token: Some(token_0),
            amount,
        })
        .await;
    suite
        .execute_message(PoolMessage::ClaimTransferReceipt {
            receipt: ClaimTransferReceipt {
                owner,
                token: token_0,
                amount,
                result: Ok(()),
            },
        })
        .await;
    assert_eq!(suite.claimable_balance(Some(token_0), owner), Amount::ZERO);
    assert_eq!(suite.claiming_balance(Some(token_0), owner), Amount::ZERO);
}

#[tokio::test(flavor = "multi_thread")]
async fn message_claim_native_rejects_meme_meme_pool() {
    let mut suite = TestSuite::create_pool(
        BootstrapPolicy::MemeInitializeLiquidity {
            virtual_initial_liquidity: false,
        },
        Some(TestSuite::token_1()),
    )
    .await;
    let owner = suite.authenticated_account();
    let amount = Amount::from_tokens(5);
    suite
        .state_app
        .borrow_mut()
        .credit_claimable(None, owner, amount)
        .blocking_wait()
        .expect("Failed to credit claimable balance");

    let result = std::panic::AssertUnwindSafe(suite.execute_message(PoolMessage::Claim {
        origin: owner,
        token: None,
        amount,
    }))
    .catch_unwind()
    .await;

    assert!(result.is_err());
    assert_eq!(suite.claimable_balance(None, owner), amount);
    assert_eq!(suite.claiming_balance(None, owner), Amount::ZERO);
}

#[tokio::test(flavor = "multi_thread")]
async fn message_claim_transfer_receipt_success_consumes_claiming() {
    let mut suite = TestSuite::create_pool(
        BootstrapPolicy::MemeInitializeLiquidity {
            virtual_initial_liquidity: false,
        },
        Some(TestSuite::token_1()),
    )
    .await;
    let owner = suite.authenticated_account();
    let token_0 = TestSuite::token_0();
    let amount = Amount::from_tokens(5);

    suite
        .contract
        .runtime
        .borrow_mut()
        .set_authenticated_caller_id(token_0);
    suite
        .state_app
        .borrow_mut()
        .credit_claimable(Some(token_0), owner, amount)
        .blocking_wait()
        .expect("Failed to credit claimable balance");
    suite
        .state_app
        .borrow_mut()
        .claim(Some(token_0), owner, amount)
        .blocking_wait()
        .expect("Failed to move balance to claiming");

    suite
        .execute_message(PoolMessage::ClaimTransferReceipt {
            receipt: ClaimTransferReceipt {
                owner,
                token: token_0,
                amount,
                result: Ok(()),
            },
        })
        .await;
    assert_eq!(suite.claimable_balance(Some(token_0), owner), Amount::ZERO);
    assert_eq!(suite.claiming_balance(Some(token_0), owner), Amount::ZERO);
}

#[tokio::test(flavor = "multi_thread")]
async fn message_claim_transfer_receipt_rejects_duplicate_success_receipt() {
    let mut suite = TestSuite::create_pool(
        BootstrapPolicy::MemeInitializeLiquidity {
            virtual_initial_liquidity: false,
        },
        Some(TestSuite::token_1()),
    )
    .await;
    let owner = suite.authenticated_account();
    let token_0 = TestSuite::token_0();
    let amount = Amount::from_tokens(5);

    suite
        .contract
        .runtime
        .borrow_mut()
        .set_authenticated_caller_id(token_0);
    suite
        .state_app
        .borrow_mut()
        .credit_claimable(Some(token_0), owner, amount)
        .blocking_wait()
        .expect("Failed to credit claimable balance");
    suite
        .state_app
        .borrow_mut()
        .claim(Some(token_0), owner, amount)
        .blocking_wait()
        .expect("Failed to move balance to claiming");

    let receipt = ClaimTransferReceipt {
        owner,
        token: token_0,
        amount,
        result: Ok(()),
    };
    suite
        .execute_message(PoolMessage::ClaimTransferReceipt {
            receipt: receipt.clone(),
        })
        .await;

    let result = std::panic::AssertUnwindSafe(suite.execute_message(
        PoolMessage::ClaimTransferReceipt { receipt },
    ))
    .catch_unwind()
    .await;

    assert!(result.is_err());
    assert_eq!(suite.claimable_balance(Some(token_0), owner), Amount::ZERO);
    assert_eq!(suite.claiming_balance(Some(token_0), owner), Amount::ZERO);
}

#[tokio::test(flavor = "multi_thread")]
async fn operation_claim_transfer_receipt_rejects_invalid_caller() {
    let mut suite = TestSuite::create_pool(
        BootstrapPolicy::MemeInitializeLiquidity {
            virtual_initial_liquidity: false,
        },
        Some(TestSuite::token_1()),
    )
    .await;
    let owner = suite.authenticated_account();
    let token_0 = TestSuite::token_0();
    let amount = Amount::from_tokens(5);

    suite
        .contract
        .runtime
        .borrow_mut()
        .set_authenticated_caller_id(TestSuite::token_1());
    suite
        .state_app
        .borrow_mut()
        .credit_claimable(Some(token_0), owner, amount)
        .blocking_wait()
        .expect("Failed to credit claimable balance");
    suite
        .state_app
        .borrow_mut()
        .claim(Some(token_0), owner, amount)
        .blocking_wait()
        .expect("Failed to move balance to claiming");

    let result = std::panic::AssertUnwindSafe(suite.execute_operation(
        PoolOperation::ClaimTransferReceipt {
            receipt: ClaimTransferReceipt {
                owner,
                token: token_0,
                amount,
                result: Ok(()),
            },
        },
    ))
    .catch_unwind()
    .await;

    assert!(result.is_err());
    assert_eq!(suite.claimable_balance(Some(token_0), owner), Amount::ZERO);
    assert_eq!(suite.claiming_balance(Some(token_0), owner), amount);
}

#[tokio::test(flavor = "multi_thread")]
async fn message_claim_transfer_receipt_rejects_non_creator_chain() {
    let mut suite = TestSuite::create_pool(
        BootstrapPolicy::MemeInitializeLiquidity {
            virtual_initial_liquidity: false,
        },
        Some(TestSuite::token_1()),
    )
    .await;
    let owner = suite.authenticated_account();
    let token_0 = TestSuite::token_0();
    let amount = Amount::from_tokens(5);
    let user_chain_id =
        ChainId::from_str("bee928d4bf3880353b4a3cd9b6f88e6cc6e5ed050860abae439e7782e9b2dfe8")
            .unwrap();

    suite
        .contract
        .runtime
        .borrow_mut()
        .set_authenticated_caller_id(token_0);
    suite
        .state_app
        .borrow_mut()
        .credit_claimable(Some(token_0), owner, amount)
        .blocking_wait()
        .expect("Failed to credit claimable balance");
    suite
        .state_app
        .borrow_mut()
        .claim(Some(token_0), owner, amount)
        .blocking_wait()
        .expect("Failed to move balance to claiming");
    suite
        .contract
        .runtime
        .borrow_mut()
        .set_chain_id(user_chain_id);

    let result = std::panic::AssertUnwindSafe(suite.execute_message(
        PoolMessage::ClaimTransferReceipt {
            receipt: ClaimTransferReceipt {
                owner,
                token: token_0,
                amount,
                result: Ok(()),
            },
        },
    ))
    .catch_unwind()
    .await;

    assert!(result.is_err());
    assert_eq!(suite.claimable_balance(Some(token_0), owner), Amount::ZERO);
    assert_eq!(suite.claiming_balance(Some(token_0), owner), amount);
}

#[tokio::test(flavor = "multi_thread")]
async fn message_claim_transfer_receipt_fail_returns_to_claimable() {
    let mut suite = TestSuite::create_pool(
        BootstrapPolicy::MemeInitializeLiquidity {
            virtual_initial_liquidity: false,
        },
        Some(TestSuite::token_1()),
    )
    .await;
    let owner = suite.authenticated_account();
    let token_0 = TestSuite::token_0();
    let amount = Amount::from_tokens(5);

    suite
        .contract
        .runtime
        .borrow_mut()
        .set_authenticated_caller_id(token_0);
    suite
        .state_app
        .borrow_mut()
        .credit_claimable(Some(token_0), owner, amount)
        .blocking_wait()
        .expect("Failed to credit claimable balance");
    suite
        .state_app
        .borrow_mut()
        .claim(Some(token_0), owner, amount)
        .blocking_wait()
        .expect("Failed to move balance to claiming");

    suite
        .execute_message(PoolMessage::ClaimTransferReceipt {
            receipt: ClaimTransferReceipt {
                owner,
                token: token_0,
                amount,
                result: Err("transfer failed".to_string()),
            },
        })
        .await;

    assert_eq!(suite.claimable_balance(Some(token_0), owner), amount);
    assert_eq!(suite.claiming_balance(Some(token_0), owner), Amount::ZERO);
}

#[tokio::test(flavor = "multi_thread")]
async fn message_claim_transfer_receipt_rejects_insufficient_claiming() {
    let mut suite = TestSuite::create_pool(
        BootstrapPolicy::MemeInitializeLiquidity {
            virtual_initial_liquidity: false,
        },
        Some(TestSuite::token_1()),
    )
    .await;
    let owner = suite.authenticated_account();
    let token_0 = TestSuite::token_0();
    let amount = Amount::from_tokens(5);

    suite
        .contract
        .runtime
        .borrow_mut()
        .set_authenticated_caller_id(token_0);

    let result = std::panic::AssertUnwindSafe(suite.execute_message(
        PoolMessage::ClaimTransferReceipt {
            receipt: ClaimTransferReceipt {
                owner,
                token: token_0,
                amount,
                result: Ok(()),
            },
        },
    ))
    .catch_unwind()
    .await;

    assert!(result.is_err());
    assert_eq!(suite.claiming_balance(Some(token_0), owner), Amount::ZERO);
}

#[tokio::test(flavor = "multi_thread")]
async fn message_claim_transfer_receipt_rejects_invalid_token() {
    let mut suite = TestSuite::create_pool(
        BootstrapPolicy::MemeInitializeLiquidity {
            virtual_initial_liquidity: false,
        },
        None,
    )
    .await;
    let owner = suite.authenticated_account();
    let invalid_token =
        ApplicationId::from_str("b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bff")
            .unwrap();
    let amount = Amount::from_tokens(5);

    suite
        .contract
        .runtime
        .borrow_mut()
        .set_authenticated_caller_id(invalid_token);

    let result = std::panic::AssertUnwindSafe(suite.execute_message(
        PoolMessage::ClaimTransferReceipt {
            receipt: ClaimTransferReceipt {
                owner,
                token: invalid_token,
                amount,
                result: Ok(()),
            },
        },
    ))
    .catch_unwind()
    .await;

    assert!(result.is_err());
}

fn add_liquidity_fund_request(
    from: Account,
    token: Option<ApplicationId>,
    amount_in: Amount,
    counterparty_token: Option<ApplicationId>,
    counterparty_amount_in: Option<Amount>,
) -> FundRequest {
    FundRequest {
        from,
        token,
        amount_in,
        amount_out_min: None,
        counterparty_token,
        counterparty_amount_in,
        counterparty_amount_out_min: None,
        to: None,
        block_timestamp: None,
        fund_type: FundType::AddLiquidity,
    }
}

#[tokio::test(flavor = "multi_thread")]
async fn message_fund_result_success_funds_pool_chain_with_receipt() {
    let mut suite = TestSuite::create_pool(
        BootstrapPolicy::MemeInitializeLiquidity {
            virtual_initial_liquidity: false,
        },
        Some(TestSuite::token_1()),
    )
    .await;
    let token_0 = TestSuite::token_0();
    let token_1 = TestSuite::token_1();
    let token_chain = TestSuite::mock_token_creator_chain_id();
    let owner = suite.authenticated_account();
    let request = add_liquidity_fund_request(
        owner,
        Some(token_0),
        Amount::ONE,
        Some(token_1),
        Some(Amount::from_tokens(10)),
    );
    let next = add_liquidity_fund_request(
        owner,
        Some(token_1),
        Amount::from_tokens(10),
        Some(token_0),
        Some(Amount::ONE),
    );

    suite.configure_fund_result_source(token_chain, owner);

    let captured = std::rc::Rc::new(std::cell::RefCell::new(None));
    let captured_for_handler = captured.clone();
    let state_app = suite.state_app.clone();
    suite
        .contract
        .runtime
        .borrow_mut()
        .set_call_application_handler(move |_authenticated, application_id, operation| {
            if application_id == TestSuite::state_application_id() {
                dispatch_state_operation(&mut state_app.borrow_mut(), &operation)
            } else {
                *captured_for_handler.borrow_mut() = Some((application_id, operation));
                bcs::to_bytes(&MemeResponse::Ok).expect("Failed to serialize mock response")
            }
        });

    suite
        .execute_message(PoolMessage::FundResult {
            prev: None,
            request: request.clone(),
            next: Some(next.clone()),
            result: Ok(()),
        })
        .await;

    let (application_id, operation) = captured.borrow().clone().unwrap();
    assert_eq!(application_id, token_0);

    let pool_chain_id = suite
        .contract
        .runtime
        .borrow_mut()
        .application_creator_chain_id();
    let pool_account = Account {
        chain_id: pool_chain_id,
        owner: AccountOwner::from(TestSuite::pool_application_id().forget_abi()),
    };

    assert!(matches!(
        bcs::from_bytes::<MemeOperation>(&operation).unwrap(),
        MemeOperation::TransferFromApplicationWithReceipt {
            to,
            amount,
            receipt,
        } if to == pool_account
        && amount == request.amount_in
        && receipt.purpose == TransferFromApplicationReceiptPurpose::PoolAddLiquidity
        && receipt.owner == owner
        && receipt.token == token_0
        && receipt.amount == request.amount_in
        && receipt.result.is_none()
        && matches!(
            &receipt.payload,
            Some(TransferFromApplicationReceiptPayload::PoolAddLiquidity(payload))
                if payload.prev.is_none()
                    && payload.request.amount_in == request.amount_in
                    && payload.next.as_ref().map(|value| value.amount_in) == Some(next.amount_in)
        )
    ));

    assert!(!suite
        .contract
        .runtime
        .borrow()
        .created_send_message_requests()
        .iter()
        .any(|request| matches!(request.message, PoolMessage::AddLiquidity { .. })));
}

#[tokio::test(flavor = "multi_thread")]
async fn message_fund_result_fail_credits_prev_without_funding_pool_chain() {
    let mut suite = TestSuite::create_pool(
        BootstrapPolicy::MemeInitializeLiquidity {
            virtual_initial_liquidity: false,
        },
        Some(TestSuite::token_1()),
    )
    .await;
    let token_0 = TestSuite::token_0();
    let token_1 = TestSuite::token_1();
    let token_chain = TestSuite::mock_token_creator_chain_id();
    let owner = suite.authenticated_account();
    let prev = add_liquidity_fund_request(
        owner,
        Some(token_0),
        Amount::ONE,
        Some(token_1),
        Some(Amount::from_tokens(10)),
    );
    let request = add_liquidity_fund_request(
        owner,
        Some(token_1),
        Amount::from_tokens(10),
        Some(token_0),
        Some(Amount::ONE),
    );

    suite.configure_fund_result_source(token_chain, owner);

    let captured = std::rc::Rc::new(std::cell::RefCell::new(None));
    let captured_for_handler = captured.clone();
    let state_app = suite.state_app.clone();
    suite
        .contract
        .runtime
        .borrow_mut()
        .set_call_application_handler(move |_authenticated, application_id, operation| {
            if application_id == TestSuite::state_application_id() {
                dispatch_state_operation(&mut state_app.borrow_mut(), &operation)
            } else {
                *captured_for_handler.borrow_mut() = Some((application_id, operation));
                bcs::to_bytes(&MemeResponse::Ok).expect("Failed to serialize mock response")
            }
        });

    suite
        .execute_message(PoolMessage::FundResult {
            prev: Some(prev.clone()),
            request,
            next: None,
            result: Err("fund failed".to_string()),
        })
        .await;

    assert!(captured.borrow().is_none());
    assert_eq!(
        suite.claimable_balance(Some(token_0), owner),
        prev.amount_in
    );
}

#[tokio::test(flavor = "multi_thread")]
async fn operation_add_liquidity_transfer_receipt_success_continues_next_fungible_leg() {
    let mut suite = TestSuite::create_pool(
        BootstrapPolicy::MemeInitializeLiquidity {
            virtual_initial_liquidity: false,
        },
        Some(TestSuite::token_1()),
    )
    .await;
    let token_0 = TestSuite::token_0();
    let token_1 = TestSuite::token_1();
    let owner = suite.authenticated_account();
    let request = add_liquidity_fund_request(
        owner,
        Some(token_0),
        Amount::ONE,
        Some(token_1),
        Some(Amount::from_tokens(10)),
    );
    let next = add_liquidity_fund_request(
        owner,
        Some(token_1),
        Amount::from_tokens(10),
        Some(token_0),
        Some(Amount::ONE),
    );

    suite
        .contract
        .runtime
        .borrow_mut()
        .set_authenticated_caller_id(token_0);

    suite
        .execute_operation(PoolOperation::AddLiquidityTransferReceipt {
            receipt: AddLiquidityTransferReceipt {
                result: Ok(()),
                prev: None,
                request: request.clone(),
                next: Some(next.clone()),
            },
        })
        .await;

    let runtime = suite.contract.runtime.borrow();
    let requests = runtime.created_send_message_requests();
    let request_message = requests
        .iter()
        .find(|request| matches!(request.message, PoolMessage::RequestFund { .. }))
        .unwrap();
    assert!(request_message.authenticated);
    assert!(!request_message.is_tracked);
    assert!(matches!(
        &request_message.message,
        PoolMessage::RequestFund {
            prev,
            request: current,
            next: following,
        } if prev.as_ref().map(|value| value.amount_in) == Some(request.amount_in)
            && current.amount_in == next.amount_in
            && following.is_none()
    ));
}

#[tokio::test(flavor = "multi_thread")]
async fn operation_add_liquidity_transfer_receipt_fail_forwards_without_successor() {
    let mut suite = TestSuite::create_pool(
        BootstrapPolicy::MemeInitializeLiquidity {
            virtual_initial_liquidity: false,
        },
        None,
    )
    .await;
    let token_0 = TestSuite::token_0();
    let owner = suite.authenticated_account();
    let prev = add_liquidity_fund_request(
        owner,
        Some(token_0),
        Amount::ONE,
        None,
        Some(Amount::from_tokens(10)),
    );
    let request = add_liquidity_fund_request(
        owner,
        Some(token_0),
        Amount::ONE,
        None,
        Some(Amount::from_tokens(10)),
    );
    let next = add_liquidity_fund_request(
        owner,
        None,
        Amount::from_tokens(10),
        Some(token_0),
        Some(Amount::ONE),
    );
    let application_owner = AccountOwner::from(TestSuite::pool_application_id().forget_abi());
    let destination = suite
        .contract
        .runtime
        .borrow_mut()
        .application_creator_chain_id();

    let mut runtime = suite.contract.runtime.borrow_mut();
    runtime.set_authenticated_caller_id(token_0);
    runtime.set_chain_balance(Amount::from_tokens(10));
    runtime.set_owner_balance(owner.owner, Amount::from_tokens(10));
    runtime.set_owner_balance(application_owner, Amount::ZERO);
    drop(runtime);

    suite
        .execute_operation(PoolOperation::AddLiquidityTransferReceipt {
            receipt: AddLiquidityTransferReceipt {
                result: Err("transfer failed".to_string()),
                prev: Some(prev.clone()),
                request: request.clone(),
                next: Some(next),
            },
        })
        .await;

    assert_eq!(
        suite
            .contract
            .runtime
            .borrow_mut()
            .owner_balance(application_owner),
        Amount::ZERO
    );

    let runtime = suite.contract.runtime.borrow();
    let requests = runtime.created_send_message_requests();
    assert!(!requests
        .iter()
        .any(|request| matches!(request.message, PoolMessage::RequestFund { .. })));
    let forwarded = requests
        .iter()
        .find(|request| {
            matches!(
                request.message,
                PoolMessage::AddLiquidityTransferReceipt { .. }
            )
        })
        .unwrap();
    assert_eq!(forwarded.destination, destination);
    assert!(matches!(
        &forwarded.message,
        PoolMessage::AddLiquidityTransferReceipt { receipt }
            if receipt.result.is_err()
                && receipt.prev.as_ref().map(|value| value.amount_in) == Some(prev.amount_in)
                && receipt.request.amount_in == request.amount_in
                && receipt.next.is_some()
    ));
}

#[tokio::test(flavor = "multi_thread")]
async fn operation_add_liquidity_transfer_receipt_success_forwards_last_leg_to_pool_creator_chain()
{
    let mut suite = TestSuite::create_pool(
        BootstrapPolicy::MemeInitializeLiquidity {
            virtual_initial_liquidity: false,
        },
        Some(TestSuite::token_1()),
    )
    .await;
    let token_0 = TestSuite::token_0();
    let token_1 = TestSuite::token_1();
    let owner = suite.authenticated_account();
    let prev = add_liquidity_fund_request(
        owner,
        Some(token_0),
        Amount::ONE,
        Some(token_1),
        Some(Amount::from_tokens(10)),
    );
    let request = add_liquidity_fund_request(
        owner,
        Some(token_1),
        Amount::from_tokens(10),
        Some(token_0),
        Some(Amount::ONE),
    );

    suite
        .contract
        .runtime
        .borrow_mut()
        .set_authenticated_caller_id(token_1);

    suite
        .execute_operation(PoolOperation::AddLiquidityTransferReceipt {
            receipt: AddLiquidityTransferReceipt {
                result: Ok(()),
                prev: Some(prev),
                request: request.clone(),
                next: None,
            },
        })
        .await;

    let destination = suite
        .contract
        .runtime
        .borrow_mut()
        .application_creator_chain_id();
    let runtime = suite.contract.runtime.borrow();
    let requests = runtime.created_send_message_requests();
    let request_message = requests
        .iter()
        .find(|request| {
            matches!(
                request.message,
                PoolMessage::AddLiquidityTransferReceipt { .. }
            )
        })
        .unwrap();
    assert_eq!(request_message.destination, destination);
    assert!(request_message.authenticated);
    assert!(!request_message.is_tracked);
    assert!(matches!(
        &request_message.message,
        PoolMessage::AddLiquidityTransferReceipt { receipt }
            if receipt.result.is_ok()
                && receipt.request.amount_in == request.amount_in
                && receipt.next.is_none()
    ));
}

#[tokio::test(flavor = "multi_thread")]
async fn operation_add_liquidity_transfer_receipt_success_funds_native_next_leg() {
    let mut suite = TestSuite::create_pool(
        BootstrapPolicy::MemeInitializeLiquidity {
            virtual_initial_liquidity: false,
        },
        None,
    )
    .await;
    let token_0 = TestSuite::token_0();
    let owner = suite.authenticated_account();
    let request = add_liquidity_fund_request(
        owner,
        Some(token_0),
        Amount::ONE,
        None,
        Some(Amount::from_tokens(10)),
    );
    let next = add_liquidity_fund_request(
        owner,
        None,
        Amount::from_tokens(10),
        Some(token_0),
        Some(Amount::ONE),
    );
    let application_owner = AccountOwner::from(TestSuite::pool_application_id().forget_abi());

    let mut runtime = suite.contract.runtime.borrow_mut();
    runtime.set_authenticated_caller_id(token_0);
    runtime.set_chain_balance(Amount::from_tokens(10));
    runtime.set_owner_balance(owner.owner, Amount::from_tokens(10));
    runtime.set_owner_balance(application_owner, Amount::ZERO);
    drop(runtime);

    suite
        .execute_operation(PoolOperation::AddLiquidityTransferReceipt {
            receipt: AddLiquidityTransferReceipt {
                result: Ok(()),
                prev: None,
                request,
                next: Some(next),
            },
        })
        .await;

    assert_eq!(
        suite
            .contract
            .runtime
            .borrow_mut()
            .owner_balance(application_owner),
        Amount::from_tokens(10)
    );
}

#[tokio::test(flavor = "multi_thread")]
async fn message_add_liquidity_transfer_receipt_success_finalizes_after_last_leg() {
    let mut suite = TestSuite::create_pool(
        BootstrapPolicy::MemeInitializeLiquidity {
            virtual_initial_liquidity: false,
        },
        Some(TestSuite::token_1()),
    )
    .await;
    let token_0 = TestSuite::token_0();
    let token_1 = TestSuite::token_1();
    let owner = suite.authenticated_account();
    let prev = add_liquidity_fund_request(
        owner,
        Some(token_0),
        Amount::ONE,
        Some(token_1),
        Some(Amount::from_tokens(10)),
    );
    let request = add_liquidity_fund_request(
        owner,
        Some(token_1),
        Amount::from_tokens(10),
        Some(token_0),
        Some(Amount::ONE),
    );

    suite
        .execute_message(PoolMessage::AddLiquidityTransferReceipt {
            receipt: AddLiquidityTransferReceipt {
                result: Ok(()),
                prev: Some(prev),
                request,
                next: None,
            },
        })
        .await;

    let destination = suite
        .contract
        .runtime
        .borrow_mut()
        .application_creator_chain_id();
    let runtime = suite.contract.runtime.borrow();
    let requests = runtime.created_send_message_requests();
    let request_message = requests.last().unwrap();
    assert_eq!(request_message.destination, destination);
    assert!(request_message.authenticated);
    assert!(!request_message.is_tracked);
    assert!(matches!(
        request_message.message,
        PoolMessage::AddLiquidity {
            origin,
            amount_0_in,
            amount_1_in,
            ..
        } if origin == owner
            && amount_0_in == Amount::ONE
            && amount_1_in == Amount::from_tokens(10)
    ));
}

#[tokio::test(flavor = "multi_thread")]
async fn message_add_liquidity_transfer_receipt_fail_credits_only_prev() {
    let mut suite = TestSuite::create_pool(
        BootstrapPolicy::MemeInitializeLiquidity {
            virtual_initial_liquidity: false,
        },
        Some(TestSuite::token_1()),
    )
    .await;
    let token_0 = TestSuite::token_0();
    let token_1 = TestSuite::token_1();
    let owner = suite.authenticated_account();
    let prev = add_liquidity_fund_request(
        owner,
        Some(token_0),
        Amount::ONE,
        Some(token_1),
        Some(Amount::from_tokens(10)),
    );
    let request = add_liquidity_fund_request(
        owner,
        Some(token_1),
        Amount::from_tokens(10),
        Some(token_0),
        Some(Amount::ONE),
    );
    let reserve_0_before = suite.pool().reserve_0;
    let reserve_1_before = suite.pool().reserve_1;
    let total_supply_before = suite.total_supply();
    let liquidity_before = suite.liquidity(owner);
    let message_count_before = suite
        .contract
        .runtime
        .borrow()
        .created_send_message_requests()
        .len();

    suite
        .execute_message(PoolMessage::AddLiquidityTransferReceipt {
            receipt: AddLiquidityTransferReceipt {
                result: Err("transfer failed".to_string()),
                prev: Some(prev.clone()),
                request: request.clone(),
                next: None,
            },
        })
        .await;

    assert_eq!(
        suite.claimable_balance(Some(token_0), owner),
        prev.amount_in
    );
    assert_eq!(
        suite.claimable_balance(Some(token_1), owner),
        Amount::ZERO
    );
    assert_eq!(suite.pool().reserve_0, reserve_0_before);
    assert_eq!(suite.pool().reserve_1, reserve_1_before);
    assert_eq!(suite.total_supply(), total_supply_before);
    assert_eq!(suite.liquidity(owner), liquidity_before);
    let runtime = suite.contract.runtime.borrow();
    assert!(
        runtime.created_send_message_requests()[message_count_before..]
            .iter()
            .all(|message| {
                !matches!(
                    message.message,
                    PoolMessage::AddLiquidity { .. } | PoolMessage::NewTransaction { .. }
                )
            })
    );
}

#[tokio::test(flavor = "multi_thread")]
async fn operation_add_liquidity_transfer_receipt_rejects_wrong_caller_app() {
    let mut suite = TestSuite::create_pool(
        BootstrapPolicy::MemeInitializeLiquidity {
            virtual_initial_liquidity: false,
        },
        Some(TestSuite::token_1()),
    )
    .await;
    let token_0 = TestSuite::token_0();
    let token_1 = TestSuite::token_1();
    let owner = suite.authenticated_account();
    let request = add_liquidity_fund_request(
        owner,
        Some(token_0),
        Amount::ONE,
        Some(token_1),
        Some(Amount::from_tokens(10)),
    );

    suite
        .contract
        .runtime
        .borrow_mut()
        .set_authenticated_caller_id(token_1);

    let result = std::panic::AssertUnwindSafe(suite.execute_operation(
        PoolOperation::AddLiquidityTransferReceipt {
            receipt: AddLiquidityTransferReceipt {
                result: Ok(()),
                prev: None,
                request,
                next: None,
            },
        },
    ))
    .catch_unwind()
    .await;

    assert!(result.is_err());
    assert!(suite
        .contract
        .runtime
        .borrow()
        .created_send_message_requests()
        .iter()
        .all(|request| !matches!(request.message, PoolMessage::AddLiquidity { .. })));
}

#[tokio::test(flavor = "multi_thread")]
async fn operation_add_liquidity_transfer_receipt_rejects_wrong_chain() {
    let mut suite = TestSuite::create_pool(
        BootstrapPolicy::MemeInitializeLiquidity {
            virtual_initial_liquidity: false,
        },
        Some(TestSuite::token_1()),
    )
    .await;
    let token_0 = TestSuite::token_0();
    let token_1 = TestSuite::token_1();
    let owner = suite.authenticated_account();
    let user_chain_id =
        ChainId::from_str("bee928d4bf3880353b4a3cd9b6f88e6cc6e5ed050860abae439e7782e9b2dfe8")
            .unwrap();
    let request = add_liquidity_fund_request(
        owner,
        Some(token_0),
        Amount::ONE,
        Some(token_1),
        Some(Amount::from_tokens(10)),
    );

    suite
        .contract
        .runtime
        .borrow_mut()
        .set_chain_id(user_chain_id);
    suite
        .contract
        .runtime
        .borrow_mut()
        .set_authenticated_caller_id(token_0);

    let result = std::panic::AssertUnwindSafe(suite.execute_operation(
        PoolOperation::AddLiquidityTransferReceipt {
            receipt: AddLiquidityTransferReceipt {
                result: Ok(()),
                prev: None,
                request,
                next: None,
            },
        },
    ))
    .catch_unwind()
    .await;

    assert!(result.is_err());
}

#[tokio::test(flavor = "multi_thread")]
async fn operation_add_liquidity_transfer_receipt_rejects_wrong_fund_type() {
    let mut suite = TestSuite::create_pool(
        BootstrapPolicy::MemeInitializeLiquidity {
            virtual_initial_liquidity: false,
        },
        Some(TestSuite::token_1()),
    )
    .await;
    let token_0 = TestSuite::token_0();
    let owner = suite.authenticated_account();
    let request = FundRequest::builder(owner, Some(token_0), Amount::ONE, FundType::Swap)
        .counterparty_token(Some(TestSuite::token_1()))
        .counterparty_amount_out_min(Some(Amount::from_attos(1)))
        .build();

    suite
        .contract
        .runtime
        .borrow_mut()
        .set_authenticated_caller_id(token_0);

    let result = std::panic::AssertUnwindSafe(suite.execute_operation(
        PoolOperation::AddLiquidityTransferReceipt {
            receipt: AddLiquidityTransferReceipt {
                result: Ok(()),
                prev: None,
                request,
                next: None,
            },
        },
    ))
    .catch_unwind()
    .await;

    assert!(result.is_err());
}

#[tokio::test(flavor = "multi_thread")]
async fn message_add_liquidity_transfer_receipt_rejects_wrong_chain_without_credit() {
    let mut suite = TestSuite::create_pool(
        BootstrapPolicy::MemeInitializeLiquidity {
            virtual_initial_liquidity: false,
        },
        Some(TestSuite::token_1()),
    )
    .await;
    let token_0 = TestSuite::token_0();
    let token_1 = TestSuite::token_1();
    let owner = suite.authenticated_account();
    let user_chain_id =
        ChainId::from_str("bee928d4bf3880353b4a3cd9b6f88e6cc6e5ed050860abae439e7782e9b2dfe8")
            .unwrap();
    let prev = add_liquidity_fund_request(
        owner,
        Some(token_0),
        Amount::ONE,
        Some(token_1),
        Some(Amount::from_tokens(10)),
    );
    let request = add_liquidity_fund_request(
        owner,
        Some(token_1),
        Amount::from_tokens(10),
        Some(token_0),
        Some(Amount::ONE),
    );

    suite
        .contract
        .runtime
        .borrow_mut()
        .set_chain_id(user_chain_id);

    let result = std::panic::AssertUnwindSafe(suite.execute_message(
        PoolMessage::AddLiquidityTransferReceipt {
            receipt: AddLiquidityTransferReceipt {
                result: Err("transfer failed".to_string()),
                prev: Some(prev),
                request,
                next: None,
            },
        },
    ))
    .catch_unwind()
    .await;

    assert!(result.is_err());
    assert_eq!(suite.claimable_balance(Some(token_0), owner), Amount::ZERO);
}

#[tokio::test(flavor = "multi_thread")]
async fn message_fund_result_swap_fail_does_not_credit_or_update_reserves() {
    let mut suite = TestSuite::create_initialized_pool(false, Some(TestSuite::token_1())).await;
    let token_0 = TestSuite::token_0();
    let token_chain = TestSuite::mock_token_creator_chain_id();
    let owner = suite.authenticated_account();
    let request = FundRequest::builder(owner, Some(token_0), Amount::ONE, FundType::Swap)
        .counterparty_token(Some(TestSuite::token_1()))
        .counterparty_amount_out_min(Some(Amount::from_attos(1)))
        .build();
    let reserve_0 = suite.pool().reserve_0;
    let reserve_1 = suite.pool().reserve_1;
    let message_count_before = suite
        .contract
        .runtime
        .borrow()
        .created_send_message_requests()
        .len();

    suite.configure_fund_result_source(token_chain, owner);
    suite
        .execute_message(PoolMessage::FundResult {
            prev: None,
            request: request.clone(),
            next: None,
            result: Err("fund failed".to_string()),
        })
        .await;

    assert_eq!(suite.pool().reserve_0, reserve_0);
    assert_eq!(suite.pool().reserve_1, reserve_1);
    assert_eq!(
        suite.claimable_balance(Some(token_0), owner),
        Amount::ZERO
    );
    assert_eq!(
        suite
            .contract
            .runtime
            .borrow()
            .created_send_message_requests()
            .len(),
        message_count_before
    );
}

#[tokio::test(flavor = "multi_thread")]
async fn message_fund_result_swap_success_requests_pool_chain_custody_with_receipt() {
    let mut suite = TestSuite::create_initialized_pool(false, Some(TestSuite::token_1())).await;
    let token_0 = TestSuite::token_0();
    let token_chain = TestSuite::mock_token_creator_chain_id();
    let owner = suite.authenticated_account();
    let request = FundRequest::builder(owner, Some(token_0), Amount::ONE, FundType::Swap)
        .counterparty_token(Some(TestSuite::token_1()))
        .counterparty_amount_out_min(Some(Amount::from_attos(1)))
        .build();

    suite.configure_fund_result_source(token_chain, owner);

    let captured = std::rc::Rc::new(std::cell::RefCell::new(None));
    let captured_for_handler = captured.clone();
    let state_app = suite.state_app.clone();
    suite
        .contract
        .runtime
        .borrow_mut()
        .set_call_application_handler(move |_authenticated, application_id, operation| {
            if application_id == TestSuite::state_application_id() {
                dispatch_state_operation(&mut state_app.borrow_mut(), &operation)
            } else {
                *captured_for_handler.borrow_mut() = Some((application_id, operation));
                bcs::to_bytes(&MemeResponse::Ok).expect("Failed to serialize mock response")
            }
        });

    suite
        .execute_message(PoolMessage::FundResult {
            prev: None,
            request: request.clone(),
            next: None,
            result: Ok(()),
        })
        .await;

    let (application_id, operation) = captured.borrow().clone().unwrap();
    assert_eq!(application_id, token_0);

    let pool_chain_id = suite
        .contract
        .runtime
        .borrow_mut()
        .application_creator_chain_id();
    let pool_account = Account {
        chain_id: pool_chain_id,
        owner: AccountOwner::from(TestSuite::pool_application_id().forget_abi()),
    };

    assert!(matches!(
        bcs::from_bytes::<MemeOperation>(&operation).unwrap(),
        MemeOperation::TransferFromApplicationWithReceipt {
            to,
            amount,
            receipt,
        } if to == pool_account
        && amount == request.amount_in
        && receipt.purpose == TransferFromApplicationReceiptPurpose::PoolSwap
        && receipt.owner == owner
        && receipt.token == token_0
        && receipt.amount == request.amount_in
        && receipt.result.is_none()
        && matches!(
            &receipt.payload,
            Some(TransferFromApplicationReceiptPayload::PoolSwap(payload))
                if payload.request.amount_in == request.amount_in
                    && payload.request.fund_type == FundType::Swap
        )
    ));
}

#[tokio::test(flavor = "multi_thread")]
async fn operation_swap_transfer_receipt_forwards_to_pool_creator_chain() {
    let mut suite = TestSuite::create_initialized_pool(false, Some(TestSuite::token_1())).await;
    let token_0 = TestSuite::token_0();
    let owner = suite.authenticated_account();
    let request = FundRequest::builder(owner, Some(token_0), Amount::ONE, FundType::Swap)
        .counterparty_token(Some(TestSuite::token_1()))
        .counterparty_amount_out_min(Some(Amount::from_attos(1)))
        .build();
    let destination = suite
        .contract
        .runtime
        .borrow_mut()
        .application_creator_chain_id();
    let message_count_before = suite
        .contract
        .runtime
        .borrow()
        .created_send_message_requests()
        .len();

    suite
        .contract
        .runtime
        .borrow_mut()
        .set_authenticated_caller_id(token_0);

    suite
        .execute_operation(PoolOperation::SwapTransferReceipt {
            receipt: SwapTransferReceipt {
                result: Ok(()),
                request: request.clone(),
            },
        })
        .await;

    let runtime = suite.contract.runtime.borrow();
    let messages = &runtime.created_send_message_requests()[message_count_before..];
    assert_eq!(messages.len(), 1);
    assert_eq!(messages[0].destination, destination);
    assert!(messages[0].authenticated);
    assert!(!messages[0].is_tracked);
    assert!(matches!(
        &messages[0].message,
        PoolMessage::SwapTransferReceipt { receipt }
            if receipt.result.is_ok()
                && receipt.request.amount_in == request.amount_in
                && receipt.request.fund_type == FundType::Swap
    ));
}

#[tokio::test(flavor = "multi_thread")]
async fn operation_swap_transfer_receipt_rejects_wrong_caller_app() {
    let mut suite = TestSuite::create_initialized_pool(false, Some(TestSuite::token_1())).await;
    let token_0 = TestSuite::token_0();
    let token_1 = TestSuite::token_1();
    let owner = suite.authenticated_account();
    let request = FundRequest::builder(owner, Some(token_0), Amount::ONE, FundType::Swap)
        .counterparty_token(Some(token_1))
        .counterparty_amount_out_min(Some(Amount::from_attos(1)))
        .build();

    suite
        .contract
        .runtime
        .borrow_mut()
        .set_authenticated_caller_id(token_1);

    let result = std::panic::AssertUnwindSafe(suite.execute_operation(
        PoolOperation::SwapTransferReceipt {
            receipt: SwapTransferReceipt {
                result: Ok(()),
                request,
            },
        },
    ))
    .catch_unwind()
    .await;

    assert!(result.is_err());
}

#[tokio::test(flavor = "multi_thread")]
async fn operation_swap_transfer_receipt_rejects_wrong_chain() {
    let mut suite = TestSuite::create_initialized_pool(false, Some(TestSuite::token_1())).await;
    let token_0 = TestSuite::token_0();
    let owner = suite.authenticated_account();
    let user_chain_id =
        ChainId::from_str("bee928d4bf3880353b4a3cd9b6f88e6cc6e5ed050860abae439e7782e9b2dfe8")
            .unwrap();
    let request = FundRequest::builder(owner, Some(token_0), Amount::ONE, FundType::Swap)
        .counterparty_token(Some(TestSuite::token_1()))
        .counterparty_amount_out_min(Some(Amount::from_attos(1)))
        .build();

    suite
        .contract
        .runtime
        .borrow_mut()
        .set_chain_id(user_chain_id);
    suite
        .contract
        .runtime
        .borrow_mut()
        .set_authenticated_caller_id(token_0);

    let result = std::panic::AssertUnwindSafe(suite.execute_operation(
        PoolOperation::SwapTransferReceipt {
            receipt: SwapTransferReceipt {
                result: Ok(()),
                request,
            },
        },
    ))
    .catch_unwind()
    .await;

    assert!(result.is_err());
}

#[tokio::test(flavor = "multi_thread")]
async fn operation_swap_transfer_receipt_rejects_wrong_fund_type() {
    let mut suite = TestSuite::create_initialized_pool(false, Some(TestSuite::token_1())).await;
    let token_0 = TestSuite::token_0();
    let token_1 = TestSuite::token_1();
    let owner = suite.authenticated_account();
    let request = add_liquidity_fund_request(
        owner,
        Some(token_0),
        Amount::ONE,
        Some(token_1),
        Some(Amount::from_tokens(10)),
    );

    suite
        .contract
        .runtime
        .borrow_mut()
        .set_authenticated_caller_id(token_0);

    let result = std::panic::AssertUnwindSafe(suite.execute_operation(
        PoolOperation::SwapTransferReceipt {
            receipt: SwapTransferReceipt {
                result: Ok(()),
                request,
            },
        },
    ))
    .catch_unwind()
    .await;

    assert!(result.is_err());
}

#[tokio::test(flavor = "multi_thread")]
async fn message_swap_transfer_receipt_success_queues_final_swap_on_pool_creator_chain() {
    let mut suite = TestSuite::create_initialized_pool(false, Some(TestSuite::token_1())).await;
    let token_0 = TestSuite::token_0();
    let owner = suite.authenticated_account();
    let request = FundRequest::builder(owner, Some(token_0), Amount::ONE, FundType::Swap)
        .counterparty_token(Some(TestSuite::token_1()))
        .counterparty_amount_out_min(Some(Amount::from_attos(1)))
        .build();
    let pool_application_id = TestSuite::pool_application_id().forget_abi();

    let mut runtime = suite.contract.runtime.borrow_mut();
    runtime.set_message_origin_chain_id(owner.chain_id);
    runtime.set_authenticated_caller_id(pool_application_id);
    drop(runtime);
    let message_count_before = suite
        .contract
        .runtime
        .borrow()
        .created_send_message_requests()
        .len();

    suite
        .execute_message(PoolMessage::SwapTransferReceipt {
            receipt: SwapTransferReceipt {
                result: Ok(()),
                request: request.clone(),
            },
        })
        .await;

    let runtime = suite.contract.runtime.borrow();
    let messages = &runtime.created_send_message_requests()[message_count_before..];
    assert_eq!(messages.len(), 1);
    assert!(messages[0].authenticated);
    assert!(!messages[0].is_tracked);
    assert!(matches!(
        &messages[0].message,
        PoolMessage::Swap {
            origin,
            amount_0_in: Some(amount_0_in),
            amount_1_in: None,
            amount_1_out_min,
            ..
        } if *origin == owner
            && *amount_0_in == Amount::ONE
            && *amount_1_out_min == Some(Amount::from_attos(1))
    ));
}

#[tokio::test(flavor = "multi_thread")]
async fn message_swap_transfer_receipt_fail_does_not_queue_final_swap() {
    let mut suite = TestSuite::create_initialized_pool(false, Some(TestSuite::token_1())).await;
    let token_0 = TestSuite::token_0();
    let owner = suite.authenticated_account();
    let request = FundRequest::builder(owner, Some(token_0), Amount::ONE, FundType::Swap)
        .counterparty_token(Some(TestSuite::token_1()))
        .counterparty_amount_out_min(Some(Amount::from_attos(1)))
        .build();
    let pool_application_id = TestSuite::pool_application_id().forget_abi();

    let mut runtime = suite.contract.runtime.borrow_mut();
    runtime.set_message_origin_chain_id(owner.chain_id);
    runtime.set_authenticated_caller_id(pool_application_id);
    drop(runtime);
    let message_count_before = suite
        .contract
        .runtime
        .borrow()
        .created_send_message_requests()
        .len();

    suite
        .execute_message(PoolMessage::SwapTransferReceipt {
            receipt: SwapTransferReceipt {
                result: Err("transfer failed".to_string()),
                request,
            },
        })
        .await;

    assert_eq!(
        suite
            .contract
            .runtime
            .borrow()
            .created_send_message_requests()
            .len(),
        message_count_before
    );
}

#[tokio::test(flavor = "multi_thread")]
async fn message_swap_transfer_receipt_rejects_wrong_chain_without_queue() {
    let mut suite = TestSuite::create_initialized_pool(false, Some(TestSuite::token_1())).await;
    let token_0 = TestSuite::token_0();
    let owner = suite.authenticated_account();
    let user_chain_id =
        ChainId::from_str("bee928d4bf3880353b4a3cd9b6f88e6cc6e5ed050860abae439e7782e9b2dfe8")
            .unwrap();
    let request = FundRequest::builder(owner, Some(token_0), Amount::ONE, FundType::Swap)
        .counterparty_token(Some(TestSuite::token_1()))
        .counterparty_amount_out_min(Some(Amount::from_attos(1)))
        .build();
    let pool_application_id = TestSuite::pool_application_id().forget_abi();
    let message_count_before = suite
        .contract
        .runtime
        .borrow()
        .created_send_message_requests()
        .len();

    let mut runtime = suite.contract.runtime.borrow_mut();
    runtime.set_chain_id(user_chain_id);
    runtime.set_message_origin_chain_id(owner.chain_id);
    runtime.set_authenticated_caller_id(pool_application_id);
    drop(runtime);

    let result = std::panic::AssertUnwindSafe(suite.execute_message(
        PoolMessage::SwapTransferReceipt {
            receipt: SwapTransferReceipt {
                result: Ok(()),
                request,
            },
        },
    ))
    .catch_unwind()
    .await;

    assert!(result.is_err());
    assert_eq!(
        suite
            .contract
            .runtime
            .borrow()
            .created_send_message_requests()
            .len(),
        message_count_before
    );
}

#[tokio::test(flavor = "multi_thread")]
async fn message_swap_slippage_after_custody_credits_input_claim_without_reserve_update() {
    let mut suite = TestSuite::create_initialized_pool(false, Some(TestSuite::token_1())).await;
    let owner = suite.authenticated_account();
    let reserve_0 = suite.pool().reserve_0;
    let reserve_1 = suite.pool().reserve_1;
    let amount_1_in = Amount::ONE;
    let total_supply_before = suite.total_supply();
    let liquidity_before = suite.liquidity(owner);
    let exact_amount_0_out = suite.pool().calculate_swap_amount_0(amount_1_in).unwrap();
    let message_count_before = suite
        .contract
        .runtime
        .borrow()
        .created_send_message_requests()
        .len();

    suite
        .execute_message(PoolMessage::Swap {
            origin: owner,
            amount_0_in: None,
            amount_1_in: Some(amount_1_in),
            amount_0_out_min: Some(exact_amount_0_out.try_add(Amount::from_attos(1)).unwrap()),
            amount_1_out_min: None,
            to: None,
            block_timestamp: None,
        })
        .await;

    assert_eq!(suite.pool().reserve_0, reserve_0);
    assert_eq!(suite.pool().reserve_1, reserve_1);
    assert_eq!(
        suite.claimable_balance(Some(TestSuite::token_1()), owner),
        amount_1_in
    );
    assert_eq!(suite.total_supply(), total_supply_before);
    assert_eq!(suite.liquidity(owner), liquidity_before);
    let runtime = suite.contract.runtime.borrow();
    assert!(
        runtime.created_send_message_requests()[message_count_before..]
            .iter()
            .all(|message| !matches!(message.message, PoolMessage::NewTransaction { .. }))
    );
}

#[tokio::test(flavor = "multi_thread")]
async fn message_fund_result_rejects_forged_signer_without_calling_token_app() {
    let mut suite = TestSuite::create_pool(
        BootstrapPolicy::MemeInitializeLiquidity {
            virtual_initial_liquidity: false,
        },
        Some(TestSuite::token_1()),
    )
    .await;
    let token_0 = TestSuite::token_0();
    let token_1 = TestSuite::token_1();
    let token_chain = TestSuite::mock_token_creator_chain_id();
    let owner = Account {
        chain_id: token_chain,
        owner: TestSuite::signer(),
    };
    let request = add_liquidity_fund_request(
        owner,
        Some(token_0),
        Amount::ONE,
        Some(token_1),
        Some(Amount::from_tokens(10)),
    );

    suite.configure_fund_result_source(token_chain, owner);
    suite
        .contract
        .runtime
        .borrow_mut()
        .set_authenticated_signer(Some(TestSuite::alternate_account().owner));

    let captured = std::rc::Rc::new(std::cell::RefCell::new(None));
    let captured_for_handler = captured.clone();
    let state_app = suite.state_app.clone();
    suite
        .contract
        .runtime
        .borrow_mut()
        .set_call_application_handler(move |_authenticated, application_id, operation| {
            if application_id == TestSuite::state_application_id() {
                dispatch_state_operation(&mut state_app.borrow_mut(), &operation)
            } else {
                *captured_for_handler.borrow_mut() = Some((application_id, operation));
                bcs::to_bytes(&MemeResponse::Ok).expect("Failed to serialize mock response")
            }
        });

    let result = std::panic::AssertUnwindSafe(suite.execute_message(PoolMessage::FundResult {
        prev: None,
        request,
        next: None,
        result: Ok(()),
    }))
    .catch_unwind()
    .await;

    assert!(result.is_err());
    assert!(captured.borrow().is_none());
}
