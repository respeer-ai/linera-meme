use super::super::BlobGatewayStateContract;
use abi::{
    blob_gateway::{
        state_v1::{
            BlobGatewayStateAbi, BlobGatewayStateV1Operation, BlobGatewayStateV1Response,
            StateInstantiationArgument,
        },
        BlobData, BlobDataType,
    },
    store_type::StoreType,
};
use blob_gateway_state::state::BlobGatewayStateV1;
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
    contract: BlobGatewayStateContract,
}

impl TestSuite {
    fn new() -> Self {
        let runtime = Self::runtime();
        let mut contract = BlobGatewayStateContract {
            state: Rc::new(RefCell::new(
                BlobGatewayStateV1::load(runtime.root_view_storage_context())
                    .blocking_wait()
                    .expect("Failed to read blob gateway StateV1 state"),
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

    async fn execute_operation(
        &mut self,
        operation: BlobGatewayStateV1Operation,
    ) -> BlobGatewayStateV1Response {
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

    fn runtime() -> ContractRuntime<BlobGatewayStateContract> {
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
            .with_application_id(Self::state_application_id().with_abi::<BlobGatewayStateAbi>())
            .with_chain_ownership(ChainOwnership::single(Self::operator().owner))
            .with_system_time(Timestamp::from(1))
            .with_block_height(BlockHeight::from(1))
    }

    fn blob_data(
        blob_hash: CryptoHash,
        store_type: StoreType,
        data_type: BlobDataType,
        created_at: Timestamp,
    ) -> BlobData {
        BlobData {
            store_type,
            data_type,
            blob_hash,
            creator: Self::operator(),
            created_at,
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

    fn test_hash(seed: &str) -> CryptoHash {
        CryptoHash::new(&TestString::new(seed.to_owned()))
    }
}

#[test]
fn instantiate_initializes_business_application_id() {
    let suite = TestSuite::new();
    let state = suite.contract.state.borrow();

    assert_eq!(
        state.business_application_id.get().as_ref().copied(),
        Some(TestSuite::business_application_id())
    );
}

#[test]
fn instantiate_initializes_operator() {
    let suite = TestSuite::new();
    let state = suite.contract.state.borrow();

    assert_eq!(
        state.operator.get().as_ref().copied(),
        Some(TestSuite::operator())
    );
}

#[tokio::test(flavor = "multi_thread")]
async fn create_blob_and_read_success() {
    let mut suite = TestSuite::new();
    let blob_hash = TestSuite::test_hash("blob-1");
    let blob_data = TestSuite::blob_data(
        blob_hash,
        StoreType::S3,
        BlobDataType::Image,
        Timestamp::from(1),
    );

    assert_eq!(
        suite
            .execute_operation(BlobGatewayStateV1Operation::CreateBlob {
                blob_data: blob_data.clone(),
            })
            .await,
        BlobGatewayStateV1Response::Ok
    );
    assert_eq!(
        suite
            .execute_operation(BlobGatewayStateV1Operation::Blob { blob_hash })
            .await,
        BlobGatewayStateV1Response::Blob(Some(blob_data))
    );
}

#[tokio::test(flavor = "multi_thread")]
async fn blob_read_returns_none_for_missing_blob() {
    let mut suite = TestSuite::new();
    let blob_hash = TestSuite::test_hash("blob-missing");

    assert_eq!(
        suite
            .execute_operation(BlobGatewayStateV1Operation::Blob { blob_hash })
            .await,
        BlobGatewayStateV1Response::Blob(None)
    );
}

#[tokio::test(flavor = "multi_thread")]
async fn create_blob_duplicate_hash_is_idempotent() {
    let mut suite = TestSuite::new();
    let blob_hash = TestSuite::test_hash("blob-duplicate");
    let first = TestSuite::blob_data(
        blob_hash,
        StoreType::S3,
        BlobDataType::Raw,
        Timestamp::from(1),
    );
    let second = BlobData {
        store_type: StoreType::Ipfs,
        data_type: BlobDataType::Video,
        blob_hash,
        creator: TestSuite::operator(),
        created_at: Timestamp::from(99),
    };

    assert_eq!(
        suite
            .execute_operation(BlobGatewayStateV1Operation::CreateBlob {
                blob_data: first.clone(),
            })
            .await,
        BlobGatewayStateV1Response::Ok
    );
    assert_eq!(
        suite
            .execute_operation(BlobGatewayStateV1Operation::CreateBlob { blob_data: second })
            .await,
        BlobGatewayStateV1Response::Ok
    );

    let stored = suite
        .contract
        .state
        .borrow()
        .blobs
        .get(&blob_hash)
        .await
        .unwrap()
        .unwrap();
    assert_eq!(stored, first);
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic(expected = "Not allowed")]
async fn create_blob_rejects_unbound_business_app() {
    let mut suite = TestSuite::new();
    suite.set_authenticated_caller(TestSuite::other_business_application_id());

    suite
        .execute_operation(BlobGatewayStateV1Operation::CreateBlob {
            blob_data: TestSuite::blob_data(
                TestSuite::test_hash("blob-reject"),
                StoreType::S3,
                BlobDataType::Image,
                Timestamp::from(1),
            ),
        })
        .await;
}

#[tokio::test(flavor = "multi_thread")]
async fn blobs_lists_all_blobs() {
    let mut suite = TestSuite::new();
    let blob_hash1 = TestSuite::test_hash("blob-list-1");
    let blob_hash2 = TestSuite::test_hash("blob-list-2");
    let blob_data1 = TestSuite::blob_data(
        blob_hash1,
        StoreType::S3,
        BlobDataType::Image,
        Timestamp::from(1),
    );
    let blob_data2 = TestSuite::blob_data(
        blob_hash2,
        StoreType::Ipfs,
        BlobDataType::Html,
        Timestamp::from(2),
    );

    assert_eq!(
        suite
            .execute_operation(BlobGatewayStateV1Operation::CreateBlob {
                blob_data: blob_data1.clone(),
            })
            .await,
        BlobGatewayStateV1Response::Ok
    );
    assert_eq!(
        suite
            .execute_operation(BlobGatewayStateV1Operation::CreateBlob {
                blob_data: blob_data2.clone(),
            })
            .await,
        BlobGatewayStateV1Response::Ok
    );

    let response = suite
        .execute_operation(BlobGatewayStateV1Operation::Blobs)
        .await;
    match response {
        BlobGatewayStateV1Response::Blobs(mut blobs) => {
            blobs.sort_by(|a, b| a.created_at.cmp(&b.created_at));
            assert_eq!(blobs, vec![blob_data1, blob_data2]);
        }
        _ => panic!("Unexpected response: {response:?}"),
    }
}

#[tokio::test(flavor = "multi_thread")]
async fn handoff_success() {
    let mut suite = TestSuite::new();

    assert_eq!(
        suite
            .execute_operation(BlobGatewayStateV1Operation::Handoff {
                new_business_application_id: TestSuite::other_business_application_id(),
            })
            .await,
        BlobGatewayStateV1Response::Ok
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
        .execute_operation(BlobGatewayStateV1Operation::Handoff {
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
        .execute_operation(BlobGatewayStateV1Operation::Handoff {
            new_business_application_id: TestSuite::other_business_application_id(),
        })
        .await;
}

#[tokio::test(flavor = "multi_thread")]
async fn set_operator_success() {
    let mut suite = TestSuite::new();
    let new_operator = Account {
        chain_id: TestSuite::chain_id(),
        owner: AccountOwner::from_str(
            "0x5279b3ae14d3b38e14b65a74aefe44824ea88b25c7841836e9ec77d991a5bc8f",
        )
        .unwrap(),
    };

    assert_eq!(
        suite
            .execute_operation(BlobGatewayStateV1Operation::SetOperator { new_operator })
            .await,
        BlobGatewayStateV1Response::Ok
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
        Some(new_operator)
    );
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic(expected = "Not allowed")]
async fn set_operator_rejects_unbound_business_app() {
    let mut suite = TestSuite::new();
    suite.set_authenticated_caller(TestSuite::other_business_application_id());
    let new_operator = Account {
        chain_id: TestSuite::chain_id(),
        owner: AccountOwner::from_str(
            "0x5279b3ae14d3b38e14b65a74aefe44824ea88b25c7841836e9ec77d991a5bc8f",
        )
        .unwrap(),
    };

    suite
        .execute_operation(BlobGatewayStateV1Operation::SetOperator { new_operator })
        .await;
}
