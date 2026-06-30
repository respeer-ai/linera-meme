use super::super::AmsStateContract;
use abi::ams::{
    abi::{Metadata, APPLICATION_TYPES},
    state_v1::{AmsStateAbi, AmsStateOperation, AmsStateResponse, StateInstantiationArgument},
};
use ams_state::state::AmsState;
use linera_sdk::{
    linera_base_types::{
        Account, AccountOwner, ApplicationDescription, ApplicationId, BlockHeight, ChainId,
        ChainOwnership, CryptoHash, ModuleId, TestString, Timestamp,
    },
    util::BlockingWait,
    views::View,
    Contract, ContractRuntime,
};
use std::{cell::RefCell, rc::Rc, str::FromStr};

struct TestSuite {
    contract: AmsStateContract,
}

impl TestSuite {
    fn new() -> Self {
        let runtime = Self::runtime();
        let mut contract = AmsStateContract {
            state: Rc::new(RefCell::new(
                AmsState::load(runtime.root_view_storage_context())
                    .blocking_wait()
                    .expect("Failed to read AMS StateV1 state"),
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

    async fn execute_operation(&mut self, operation: AmsStateOperation) -> AmsStateResponse {
        self.contract.execute_operation(operation).await
    }

    fn set_authenticated_caller(&mut self, caller: ApplicationId) {
        self.contract
            .runtime
            .borrow_mut()
            .set_authenticated_caller_id(caller);
    }

    fn set_application_description(&mut self, application_id: ApplicationId, chain_id: ChainId) {
        self.contract
            .runtime
            .borrow_mut()
            .set_application_description(application_id, Self::application_description(chain_id));
    }

    fn runtime() -> ContractRuntime<AmsStateContract> {
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
            .with_application_id(Self::state_application_id().with_abi::<AmsStateAbi>())
            .with_chain_ownership(ChainOwnership::single(Self::operator().owner))
            .with_system_time(Timestamp::from(1))
            .with_block_height(BlockHeight::from(1))
    }

    fn metadata(application_id: ApplicationId, application_type: &str) -> Metadata {
        Metadata {
            creator: Self::operator(),
            application_name: "Example App".to_string(),
            application_id,
            application_type: application_type.to_string(),
            key_words: vec!["example".to_string()],
            logo_store_type: abi::store_type::StoreType::S3,
            logo: CryptoHash::new(&TestString::new("logo".to_string())),
            description: "Example description".to_string(),
            twitter: None,
            telegram: None,
            discord: None,
            website: None,
            github: None,
            spec: None,
            created_at: Timestamp::from(1),
        }
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

    fn other_operator() -> Account {
        Account {
            chain_id: Self::chain_id(),
            owner: AccountOwner::from_str(
                "0x03e900512d2fca22897f80a2f6932ff454f2752ef7afad18729dd25e5b5b6e00",
            )
            .unwrap(),
        }
    }

    fn other_account() -> Account {
        Account {
            chain_id: Self::other_chain_id(),
            owner: Self::operator().owner,
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

    fn third_business_application_id() -> ApplicationId {
        Self::application_id("b40ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bad")
    }

    fn state_application_id() -> ApplicationId {
        Self::application_id("b30ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bad")
    }

    fn application_id(value: &str) -> ApplicationId {
        ApplicationId::from_str(value).unwrap()
    }
}

#[test]
fn instantiate_initializes_binding_operator_and_application_types() {
    let suite = TestSuite::new();
    let state = suite.contract.state.borrow();

    assert_eq!(
        state.business_application_id.get().as_ref().copied(),
        Some(TestSuite::business_application_id())
    );
    assert_eq!(
        state.operator.get().as_ref().copied(),
        Some(TestSuite::operator())
    );
    assert_eq!(
        state.application_types.get(),
        &APPLICATION_TYPES
            .iter()
            .map(|application_type| application_type.to_string())
            .collect::<Vec<_>>()
    );
}

#[tokio::test(flavor = "multi_thread")]
async fn register_and_read_application_success() {
    let mut suite = TestSuite::new();
    let application_id = TestSuite::application_id(
        "c10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bad",
    );
    let metadata = TestSuite::metadata(application_id, "Meme");

    assert_eq!(
        suite
            .execute_operation(AmsStateOperation::RegisterApplication {
                metadata: metadata.clone(),
            })
            .await,
        AmsStateResponse::Ok
    );
    assert_eq!(
        suite
            .execute_operation(AmsStateOperation::Application { application_id })
            .await,
        AmsStateResponse::Application(Some(metadata))
    );
}

#[tokio::test(flavor = "multi_thread")]
async fn application_read_returns_none_for_missing_application() {
    let mut suite = TestSuite::new();
    let application_id = TestSuite::application_id(
        "c20ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bad",
    );

    assert_eq!(
        suite
            .execute_operation(AmsStateOperation::Application { application_id })
            .await,
        AmsStateResponse::Application(None)
    );
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic(expected = "Not allowed")]
async fn register_application_rejects_unbound_business_app() {
    let mut suite = TestSuite::new();
    suite.set_authenticated_caller(TestSuite::other_business_application_id());
    let application_id = TestSuite::application_id(
        "c30ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bad",
    );

    suite
        .execute_operation(AmsStateOperation::RegisterApplication {
            metadata: TestSuite::metadata(application_id, "Meme"),
        })
        .await;
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic(expected = "Not allowed")]
async fn register_application_rejects_unknown_application_type() {
    let mut suite = TestSuite::new();
    let application_id = TestSuite::application_id(
        "c40ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bad",
    );

    suite
        .execute_operation(AmsStateOperation::RegisterApplication {
            metadata: TestSuite::metadata(application_id, "Analytics"),
        })
        .await;
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic(expected = "application already exists")]
async fn register_application_rejects_duplicate_application() {
    let mut suite = TestSuite::new();
    let application_id = TestSuite::application_id(
        "c50ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bad",
    );
    let metadata = TestSuite::metadata(application_id, "Meme");

    assert_eq!(
        suite
            .execute_operation(AmsStateOperation::RegisterApplication {
                metadata: metadata.clone(),
            })
            .await,
        AmsStateResponse::Ok
    );
    suite
        .execute_operation(AmsStateOperation::RegisterApplication { metadata })
        .await;
}

#[tokio::test(flavor = "multi_thread")]
async fn set_operator_success() {
    let mut suite = TestSuite::new();

    assert_eq!(
        suite
            .execute_operation(AmsStateOperation::SetOperator {
                new_operator: TestSuite::other_operator(),
            })
            .await,
        AmsStateResponse::Ok
    );
    assert_eq!(
        suite
            .contract
            .state
            .borrow()
            .operator
            .get()
            .as_ref()
            .copied(),
        Some(TestSuite::other_operator())
    );
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic(expected = "Not allowed")]
async fn set_operator_rejects_unbound_business_app() {
    let mut suite = TestSuite::new();
    suite.set_authenticated_caller(TestSuite::other_business_application_id());

    suite
        .execute_operation(AmsStateOperation::SetOperator {
            new_operator: TestSuite::operator(),
        })
        .await;
}

#[tokio::test(flavor = "multi_thread")]
async fn add_application_type_success() {
    let mut suite = TestSuite::new();

    assert_eq!(
        suite
            .execute_operation(AmsStateOperation::AddApplicationType {
                owner: TestSuite::operator(),
                application_type: "Analytics".to_string(),
            })
            .await,
        AmsStateResponse::Ok
    );
    assert!(suite
        .contract
        .state
        .borrow()
        .application_types
        .get()
        .contains(&"Analytics".to_string()));
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic(expected = "Not allowed")]
async fn add_application_type_rejects_unbound_business_app() {
    let mut suite = TestSuite::new();
    suite.set_authenticated_caller(TestSuite::other_business_application_id());

    suite
        .execute_operation(AmsStateOperation::AddApplicationType {
            owner: TestSuite::operator(),
            application_type: "Analytics".to_string(),
        })
        .await;
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic(expected = "Not allowed")]
async fn add_application_type_rejects_non_operator_owner() {
    let mut suite = TestSuite::new();

    suite
        .execute_operation(AmsStateOperation::AddApplicationType {
            owner: TestSuite::other_operator(),
            application_type: "Analytics".to_string(),
        })
        .await;
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic(expected = "application type already exists")]
async fn add_application_type_rejects_duplicate_type() {
    let mut suite = TestSuite::new();

    assert_eq!(
        suite
            .execute_operation(AmsStateOperation::AddApplicationType {
                owner: TestSuite::operator(),
                application_type: "Analytics".to_string(),
            })
            .await,
        AmsStateResponse::Ok
    );
    suite
        .execute_operation(AmsStateOperation::AddApplicationType {
            owner: TestSuite::operator(),
            application_type: "Analytics".to_string(),
        })
        .await;
}

#[tokio::test(flavor = "multi_thread")]
async fn claim_application_success() {
    let mut suite = TestSuite::new();
    let application_id = TestSuite::application_id(
        "d10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bad",
    );
    let metadata = TestSuite::metadata(application_id, "Meme");

    assert_eq!(
        suite
            .execute_operation(AmsStateOperation::RegisterApplication {
                metadata: metadata.clone(),
            })
            .await,
        AmsStateResponse::Ok
    );
    assert_eq!(
        suite
            .execute_operation(AmsStateOperation::ClaimApplication {
                owner: TestSuite::operator(),
                application_id,
            })
            .await,
        AmsStateResponse::Ok
    );
    assert_eq!(
        suite
            .execute_operation(AmsStateOperation::Application { application_id })
            .await,
        AmsStateResponse::Application(Some(metadata))
    );
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic(expected = "Not allowed")]
async fn claim_application_rejects_unbound_business_app() {
    let mut suite = TestSuite::new();
    suite.set_authenticated_caller(TestSuite::other_business_application_id());

    suite
        .execute_operation(AmsStateOperation::ClaimApplication {
            owner: TestSuite::operator(),
            application_id: TestSuite::application_id(
                "d20ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bad",
            ),
        })
        .await;
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic(expected = "Not allowed")]
async fn claim_application_rejects_missing_application() {
    let mut suite = TestSuite::new();

    suite
        .execute_operation(AmsStateOperation::ClaimApplication {
            owner: TestSuite::operator(),
            application_id: TestSuite::application_id(
                "d30ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bad",
            ),
        })
        .await;
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic(expected = "Not allowed")]
async fn claim_application_rejects_owner_mismatch() {
    let mut suite = TestSuite::new();
    let application_id = TestSuite::application_id(
        "d40ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bad",
    );

    assert_eq!(
        suite
            .execute_operation(AmsStateOperation::RegisterApplication {
                metadata: TestSuite::metadata(application_id, "Meme"),
            })
            .await,
        AmsStateResponse::Ok
    );
    suite
        .execute_operation(AmsStateOperation::ClaimApplication {
            owner: TestSuite::other_account(),
            application_id,
        })
        .await;
}

#[tokio::test(flavor = "multi_thread")]
async fn update_application_success() {
    let mut suite = TestSuite::new();
    let application_id = TestSuite::application_id(
        "e10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bad",
    );
    let metadata = TestSuite::metadata(application_id, "Meme");
    let mut updated = metadata.clone();
    updated.application_name = "Updated App".to_string();
    updated.description = "Updated description".to_string();
    updated.application_type = "Game".to_string();

    assert_eq!(
        suite
            .execute_operation(AmsStateOperation::RegisterApplication { metadata })
            .await,
        AmsStateResponse::Ok
    );
    assert_eq!(
        suite
            .execute_operation(AmsStateOperation::UpdateApplication {
                owner: TestSuite::operator(),
                application_id,
                metadata: updated.clone(),
            })
            .await,
        AmsStateResponse::Ok
    );
    assert_eq!(
        suite
            .execute_operation(AmsStateOperation::Application { application_id })
            .await,
        AmsStateResponse::Application(Some(updated))
    );
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic(expected = "Not allowed")]
async fn update_application_rejects_unbound_business_app() {
    let mut suite = TestSuite::new();
    suite.set_authenticated_caller(TestSuite::other_business_application_id());
    let application_id = TestSuite::application_id(
        "e20ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bad",
    );

    suite
        .execute_operation(AmsStateOperation::UpdateApplication {
            owner: TestSuite::operator(),
            application_id,
            metadata: TestSuite::metadata(application_id, "Meme"),
        })
        .await;
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic(expected = "Not allowed")]
async fn update_application_rejects_missing_application() {
    let mut suite = TestSuite::new();
    let application_id = TestSuite::application_id(
        "e30ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bad",
    );

    suite
        .execute_operation(AmsStateOperation::UpdateApplication {
            owner: TestSuite::operator(),
            application_id,
            metadata: TestSuite::metadata(application_id, "Meme"),
        })
        .await;
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic(expected = "Not allowed")]
async fn update_application_rejects_owner_mismatch() {
    let mut suite = TestSuite::new();
    let application_id = TestSuite::application_id(
        "e40ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bad",
    );

    assert_eq!(
        suite
            .execute_operation(AmsStateOperation::RegisterApplication {
                metadata: TestSuite::metadata(application_id, "Meme"),
            })
            .await,
        AmsStateResponse::Ok
    );
    suite
        .execute_operation(AmsStateOperation::UpdateApplication {
            owner: TestSuite::other_account(),
            application_id,
            metadata: TestSuite::metadata(application_id, "Meme"),
        })
        .await;
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic(expected = "Not allowed")]
async fn update_application_rejects_unknown_application_type() {
    let mut suite = TestSuite::new();
    let application_id = TestSuite::application_id(
        "e50ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bad",
    );

    assert_eq!(
        suite
            .execute_operation(AmsStateOperation::RegisterApplication {
                metadata: TestSuite::metadata(application_id, "Meme"),
            })
            .await,
        AmsStateResponse::Ok
    );
    suite
        .execute_operation(AmsStateOperation::UpdateApplication {
            owner: TestSuite::operator(),
            application_id,
            metadata: TestSuite::metadata(application_id, "Analytics"),
        })
        .await;
}

#[tokio::test(flavor = "multi_thread")]
async fn handoff_success() {
    let mut suite = TestSuite::new();

    assert_eq!(
        suite
            .execute_operation(AmsStateOperation::Handoff {
                new_business_application_id: TestSuite::other_business_application_id(),
            })
            .await,
        AmsStateResponse::Ok
    );
    assert_eq!(
        suite
            .contract
            .state
            .borrow()
            .business_application_id
            .get()
            .as_ref()
            .copied(),
        Some(TestSuite::other_business_application_id())
    );
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic(expected = "Not allowed")]
async fn handoff_rejects_unbound_business_app() {
    let mut suite = TestSuite::new();
    suite.set_authenticated_caller(TestSuite::other_business_application_id());

    suite
        .execute_operation(AmsStateOperation::Handoff {
            new_business_application_id: TestSuite::third_business_application_id(),
        })
        .await;
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic(expected = "Not allowed")]
async fn handoff_rejects_new_business_app_on_different_creator_chain() {
    let mut suite = TestSuite::new();
    suite.set_application_description(
        TestSuite::other_business_application_id(),
        TestSuite::other_chain_id(),
    );

    suite
        .execute_operation(AmsStateOperation::Handoff {
            new_business_application_id: TestSuite::other_business_application_id(),
        })
        .await;
}
