// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

use super::ProxyStateContract;
use abi::proxy::{
    state_v1::{
        ProxyStateAbi, ProxyStateV1Operation, ProxyStateV1Response, StateInstantiationArgument,
    },
    Chain, InitializeArgument, Miner, StateBytecodeId,
};
use linera_sdk::{
    linera_base_types::{
        Account, AccountOwner, ApplicationId, ChainId, ModuleId, Timestamp,
    },
    util::BlockingWait,
    views::View,
    Contract, ContractRuntime,
};
use proxy_state::state::ProxyState;
use std::{cell::RefCell, rc::Rc, str::FromStr};

struct TestSuite {
    contract: ProxyStateContract,
}

impl TestSuite {
    fn new() -> Self {
        let runtime = Self::runtime();
        let mut contract = ProxyStateContract {
            state: Rc::new(RefCell::new(
                ProxyState::load(runtime.root_view_storage_context())
                    .blocking_wait()
                    .expect("Failed to load proxy state v1"),
            )),
            runtime: Rc::new(RefCell::new(runtime)),
        };
        contract.instantiate(Self::instantiation_argument()).blocking_wait();
        contract
            .execute_operation(ProxyStateV1Operation::Initialize {
                argument: Self::initialize_argument(),
            })
            .blocking_wait();
        Self { contract }
    }

    fn runtime() -> ContractRuntime<ProxyStateContract> {
        ContractRuntime::new()
            .with_application_parameters(())
            .with_chain_id(Self::chain_id())
            .with_application_creator_chain_id(Self::chain_id())
            .with_application_id(Self::state_application_id().with_abi::<ProxyStateAbi>())
            .with_authenticated_signer(Self::operator().owner)
            .with_system_time(Timestamp::from(1))
    }

    fn instantiation_argument() -> StateInstantiationArgument {
        StateInstantiationArgument {
            business_application_id: Self::business_application_id(),
            operator: Some(Self::operator()),
        }
    }

    fn initialize_argument() -> InitializeArgument {
        InitializeArgument {
            initial_operators: vec![Self::operator()],
            genesis_miner_owners: vec![Self::operator()],
            swap_application_id: Self::swap_application_id(),
            meme_bytecode_id: Self::meme_bytecode_id(),
            meme_state_bytecode_ids: vec![StateBytecodeId {
                version: 1,
                module_id: Self::meme_state_bytecode_id(),
            }],
        }
    }

    async fn execute_operation(
        &mut self,
        operation: ProxyStateV1Operation,
    ) -> ProxyStateV1Response {
        self.contract.execute_operation(operation).await
    }

    fn set_authenticated_signer(&mut self, owner: AccountOwner) {
        self.contract
            .runtime
            .borrow_mut()
            .set_authenticated_signer(Some(owner));
    }

    fn chain_id() -> ChainId {
        ChainId::from_str("aee928d4bf3880353b4a3cd9b6f88e6cc6e5ed050860abae439e7782e9b2dfe8")
            .unwrap()
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
                "0x02e900512d2fca22897f80a2f6932ff454f2752ef7afad18729dd25e5b5b6e01",
            )
            .unwrap(),
        }
    }

    fn business_application_id() -> ApplicationId {
        ApplicationId::from_str("b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bad")
            .unwrap()
    }

    fn new_business_application_id() -> ApplicationId {
        ApplicationId::from_str("b20ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bad")
            .unwrap()
    }

    fn state_application_id() -> ApplicationId {
        ApplicationId::from_str("b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bae")
            .unwrap()
    }

    fn swap_application_id() -> ApplicationId {
        ApplicationId::from_str("b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5baf")
            .unwrap()
    }

    fn meme_bytecode_id() -> ModuleId {
        ModuleId::from_str("b94e486abcfc016e937dad4297523060095f405530c95d498d981a94141589f167693295a14c3b48460ad6f75d67d2414428227550eb8cee8ecaa37e8646518300").unwrap()
    }

    fn meme_state_bytecode_id() -> ModuleId {
        ModuleId::from_str("a94e486abcfc016e937dad4297523060095f405530c95d498d981a94141589f167693295a14c3b48460ad6f75d67d2414428227550eb8cee8ecaa37e8646518300").unwrap()
    }

    fn new_meme_bytecode_id() -> ModuleId {
        ModuleId::from_str("c94e486abcfc016e937dad4297523060095f405530c95d498d981a94141589f167693295a14c3b48460ad6f75d67d2414428227550eb8cee8ecaa37e8646518300").unwrap()
    }

    fn new_meme_state_bytecode_id() -> ModuleId {
        ModuleId::from_str("d94e486abcfc016e937dad4297523060095f405530c95d498d981a94141589f167693295a14c3b48460ad6f75d67d2414428227550eb8cee8ecaa37e8646518300").unwrap()
    }

    fn chain_id_2() -> ChainId {
        ChainId::from_str("abdb7c1079f36eaa03f629540283a881eb4256d1ece83a84415022d4d2a9ac65")
            .unwrap()
    }

    fn token_application_id() -> ApplicationId {
        ApplicationId::from_str("c10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bad")
            .unwrap()
    }
}

#[tokio::test(flavor = "multi_thread")]
async fn instantiate_initializes_state() {
    let suite = TestSuite::new();
    let state = suite.contract.state.borrow();

    assert_eq!(
        *state.business_application_id.get(),
        Some(TestSuite::business_application_id())
    );
    assert_eq!(*state.operator.get(), Some(TestSuite::operator()));
    assert_eq!(*state.meme_bytecode_id.get(), Some(TestSuite::meme_bytecode_id()));
    assert_eq!(
        *state.swap_application_id.get(),
        Some(TestSuite::swap_application_id())
    );
    assert!(state.operators.contains_key(&TestSuite::operator()).blocking_wait().unwrap());
    assert!(state.genesis_miners.contains_key(&TestSuite::operator()).blocking_wait().unwrap());
}

#[tokio::test(flavor = "multi_thread")]
async fn set_meme_bytecode_ids_updates_business_and_state_bytecodes() {
    let mut suite = TestSuite::new();

    let response = suite
        .execute_operation(ProxyStateV1Operation::SetMemeBytecodeIds {
            business_bytecode_id: TestSuite::new_meme_bytecode_id(),
            state_bytecode_id: TestSuite::new_meme_state_bytecode_id(),
        })
        .await;
    assert_eq!(response, ProxyStateV1Response::Ok);

    let state = suite.contract.state.borrow();
    assert_eq!(
        *state.meme_bytecode_id.get(),
        Some(TestSuite::new_meme_bytecode_id())
    );
    let ids = state
        .meme_state_bytecode_ids
        .index_values()
        .blocking_wait()
        .unwrap();
    assert_eq!(ids, vec![(1u16, TestSuite::meme_state_bytecode_id()), (2u16, TestSuite::new_meme_state_bytecode_id())]);
}

#[tokio::test(flavor = "multi_thread")]
async fn add_operator_creates_pending_operator() {
    let mut suite = TestSuite::new();
    let owner = TestSuite::other_account();

    let response = suite
        .execute_operation(ProxyStateV1Operation::AddOperator { owner })
        .await;
    assert_eq!(response, ProxyStateV1Response::Ok);

    let state = suite.contract.state.borrow();
    assert!(state.operators.contains_key(&owner).blocking_wait().unwrap());
}

#[tokio::test(flavor = "multi_thread")]
async fn approve_add_operator_second_vote_completes_approval() {
    let mut suite = TestSuite::new();
    let owner = TestSuite::other_account();

    suite
        .execute_operation(ProxyStateV1Operation::AddOperator { owner })
        .await;

    let response = suite
        .execute_operation(ProxyStateV1Operation::ApproveAddOperator {
            owner,
            operator: TestSuite::operator(),
        })
        .await;
    assert_eq!(response, ProxyStateV1Response::Ok);

    let state = suite.contract.state.borrow();
    let approval = state.operators.get(&owner).blocking_wait().unwrap().unwrap();
    assert!(approval.approved());
}

#[tokio::test(flavor = "multi_thread")]
async fn ban_operator_then_approve_ban_operator_removes_operator() {
    let mut suite = TestSuite::new();
    let owner = TestSuite::operator();

    suite
        .execute_operation(ProxyStateV1Operation::BanOperator { owner })
        .await;

    let response = suite
        .execute_operation(ProxyStateV1Operation::ApproveBanOperator {
            owner,
            operator: owner,
        })
        .await;
    assert_eq!(response, ProxyStateV1Response::Ok);

    let state = suite.contract.state.borrow();
    assert!(!state.operators.contains_key(&owner).blocking_wait().unwrap());
    assert!(!state.banning_operators.contains_key(&owner).blocking_wait().unwrap());
}

#[tokio::test(flavor = "multi_thread")]
async fn add_genesis_miner_creates_pending_genesis_miner() {
    let mut suite = TestSuite::new();
    let owner = TestSuite::other_account();

    let response = suite
        .execute_operation(ProxyStateV1Operation::AddGenesisMiner { owner })
        .await;
    assert_eq!(response, ProxyStateV1Response::Ok);

    let state = suite.contract.state.borrow();
    assert!(state.genesis_miners.contains_key(&owner).blocking_wait().unwrap());
}

#[tokio::test(flavor = "multi_thread")]
async fn approve_add_genesis_miner_second_vote_completes_approval() {
    let mut suite = TestSuite::new();
    let owner = TestSuite::other_account();

    suite
        .execute_operation(ProxyStateV1Operation::AddGenesisMiner { owner })
        .await;

    let response = suite
        .execute_operation(ProxyStateV1Operation::ApproveAddGenesisMiner {
            owner,
            operator: TestSuite::operator(),
        })
        .await;
    assert_eq!(response, ProxyStateV1Response::Ok);

    let state = suite.contract.state.borrow();
    let miner = state.genesis_miners.get(&owner).blocking_wait().unwrap().unwrap();
    assert!(miner.approval.approved());
}

#[tokio::test(flavor = "multi_thread")]
async fn remove_genesis_miner_then_approve_removes_miner() {
    let mut suite = TestSuite::new();
    let owner = TestSuite::operator();

    suite
        .execute_operation(ProxyStateV1Operation::RemoveGenesisMiner { owner })
        .await;

    let response = suite
        .execute_operation(ProxyStateV1Operation::ApproveRemoveGenesisMiner {
            owner,
            operator: owner,
        })
        .await;
    assert_eq!(response, ProxyStateV1Response::Ok);

    let state = suite.contract.state.borrow();
    assert!(!state.genesis_miners.contains_key(&owner).blocking_wait().unwrap());
    assert!(!state.removing_genesis_miners.contains_key(&owner).blocking_wait().unwrap());
}

#[tokio::test(flavor = "multi_thread")]
async fn register_miner_then_deregister_miner() {
    let mut suite = TestSuite::new();

    suite.set_authenticated_signer(TestSuite::other_account().owner);
    let response = suite.execute_operation(ProxyStateV1Operation::RegisterMiner {
            owner: TestSuite::other_account(),
            now: Timestamp::from(2),
        }).await;
    assert_eq!(response, ProxyStateV1Response::Ok);

    let state = suite.contract.state.borrow();
    assert!(state.miners.contains_key(&TestSuite::other_account()).blocking_wait().unwrap());
    drop(state);

    let response = suite
        .execute_operation(ProxyStateV1Operation::DeregisterMiner {
            owner: TestSuite::other_account(),
        })
        .await;
    assert_eq!(response, ProxyStateV1Response::Ok);

    let state = suite.contract.state.borrow();
    assert!(!state.miners.contains_key(&TestSuite::other_account()).blocking_wait().unwrap());
}

#[tokio::test(flavor = "multi_thread")]
async fn create_chain_then_create_chain_token_then_query() {
    let mut suite = TestSuite::new();
    let chain_id = TestSuite::chain_id_2();
    let token = TestSuite::token_application_id();

    let response = suite
        .execute_operation(ProxyStateV1Operation::CreateChain {
            chain_id,
            created_at: Timestamp::from(2),
        })
        .await;
    assert_eq!(response, ProxyStateV1Response::Ok);

    let response = suite
        .execute_operation(ProxyStateV1Operation::CreateChainToken { chain_id, token })
        .await;
    assert_eq!(response, ProxyStateV1Response::Ok);

    let response = suite
        .execute_operation(ProxyStateV1Operation::Chain { chain_id })
        .await;
    let created_at = Timestamp::from(1);
    assert_eq!(
        response,
        ProxyStateV1Response::Chain(Some(Chain {
            chain_id,
            created_at,
            token: Some(token),
        }))
    );

    let response = suite
        .execute_operation(ProxyStateV1Operation::ChainByToken { token })
        .await;
    assert_eq!(
        response,
        ProxyStateV1Response::Chain(Some(Chain {
            chain_id,
            created_at,
            token: Some(token),
        }))
    );

    let response = suite
        .execute_operation(ProxyStateV1Operation::Chains {
            created_after: Some(Timestamp::from(0)),
        })
        .await;
    assert_eq!(
        response,
        ProxyStateV1Response::Chains(vec![Chain {
            chain_id,
            created_at,
            token: Some(token),
        }])
    );
}

#[tokio::test(flavor = "multi_thread")]
async fn bytecode_and_swap_queries_return_instantiated_values() {
    let mut suite = TestSuite::new();

    let response = suite
        .execute_operation(ProxyStateV1Operation::MemeBytecodeId)
        .await;
    assert_eq!(
        response,
        ProxyStateV1Response::ModuleId(TestSuite::meme_bytecode_id())
    );

    let response = suite
        .execute_operation(ProxyStateV1Operation::MemeStateBytecodeIds)
        .await;
    assert_eq!(
        response,
        ProxyStateV1Response::ModuleIds(vec![(1, TestSuite::meme_state_bytecode_id())])
    );

    let response = suite
        .execute_operation(ProxyStateV1Operation::SwapApplicationId)
        .await;
    assert_eq!(
        response,
        ProxyStateV1Response::ApplicationId(TestSuite::swap_application_id())
    );
}

#[tokio::test(flavor = "multi_thread")]
async fn miner_read_queries_return_registered_miners() {
    let mut suite = TestSuite::new();

    suite.set_authenticated_signer(TestSuite::other_account().owner);
    suite
        .execute_operation(ProxyStateV1Operation::RegisterMiner {
            owner: TestSuite::other_account(),
            now: Timestamp::from(2),
        })
        .await;

    let operator = TestSuite::operator();
    let response = suite
        .execute_operation(ProxyStateV1Operation::IsGenesisMiner {
            owner: operator,
        })
        .await;
    assert_eq!(response, ProxyStateV1Response::Bool(true));

    let response = suite
        .execute_operation(ProxyStateV1Operation::GenesisMiners)
        .await;
    assert_eq!(
        response,
        ProxyStateV1Response::Miners(vec![Miner {
            owner: operator,
            registered_at: 0.into(),
        }])
    );

    let response = suite.execute_operation(ProxyStateV1Operation::Miners).await;
    assert_eq!(
        response,
        ProxyStateV1Response::Miners(vec![
            Miner {
                owner: TestSuite::other_account(),
                registered_at: Timestamp::from(1),
            },
            Miner {
                owner: operator,
                registered_at: 0.into(),
            },
        ])
    );

    let response = suite
        .execute_operation(ProxyStateV1Operation::MinerOwners)
        .await;
    assert_eq!(
        response,
        ProxyStateV1Response::AccountOwners(vec![
            TestSuite::other_account().owner,
            operator.owner,
        ])
    );
}

#[tokio::test(flavor = "multi_thread")]
async fn validate_operator_succeeds_for_approved_operator() {
    let mut suite = TestSuite::new();

    let response = suite
        .execute_operation(ProxyStateV1Operation::ValidateOperator {
            owner: TestSuite::operator(),
        })
        .await;
    assert_eq!(response, ProxyStateV1Response::Ok);
}

#[tokio::test(flavor = "multi_thread")]
async fn set_operator_updates_operator() {
    let mut suite = TestSuite::new();
    let new_operator = TestSuite::other_account();

    let response = suite
        .execute_operation(ProxyStateV1Operation::SetOperator { new_operator })
        .await;
    assert_eq!(response, ProxyStateV1Response::Ok);

    let state = suite.contract.state.borrow();
    assert_eq!(*state.operator.get(), Some(new_operator));
}

#[tokio::test(flavor = "multi_thread")]
async fn handoff_updates_business_application_id() {
    let mut suite = TestSuite::new();

    let response = suite
        .execute_operation(ProxyStateV1Operation::Handoff {
            new_business_application_id: TestSuite::new_business_application_id(),
        })
        .await;
    assert_eq!(response, ProxyStateV1Response::Ok);

    let state = suite.contract.state.borrow();
    assert_eq!(
        *state.business_application_id.get(),
        Some(TestSuite::new_business_application_id())
    );
}
