#![cfg(not(target_arch = "wasm32"))]

use abi::{
    blob_gateway::{
        state_v1::{BlobGatewayStateAbi, StateInstantiationArgument},
        BlobData, BlobDataType, BlobGatewayAbi, BlobGatewayOperation,
    },
    store_type::StoreType,
};
use async_graphql::Request;
use linera_sdk::{
    linera_base_types::{Account, AccountOwner, ApplicationId, CryptoHash, ModuleId, TestString},
    test::{ActiveChain, TestValidator},
};

struct TestSuite {
    blob_gateway_creator_chain: ActiveChain,
    user_chain: ActiveChain,
    blob_gateway_application_id: ApplicationId<BlobGatewayAbi>,
    state_application_id: ApplicationId<BlobGatewayStateAbi>,
    blob_gateway_bytecode_id: ModuleId<BlobGatewayAbi, (), ()>,
}

impl TestSuite {
    async fn new() -> Self {
        let (validator, blob_gateway_bytecode_id) =
            TestValidator::with_current_module::<BlobGatewayAbi, (), ()>().await;
        let mut blob_gateway_creator_chain = validator.new_chain().await;
        let user_chain = validator.new_chain().await;

        let blob_gateway_application_id = blob_gateway_creator_chain
            .create_application::<BlobGatewayAbi, (), ()>(
                blob_gateway_bytecode_id.clone(),
                (),
                (),
                vec![],
            )
            .await;

        let state_bytecode_id = blob_gateway_creator_chain
            .publish_bytecode_files_in("../state")
            .await;
        let state_application_id = blob_gateway_creator_chain
            .create_application::<BlobGatewayStateAbi, (), StateInstantiationArgument>(
                state_bytecode_id,
                (),
                StateInstantiationArgument {
                    business_application_id: blob_gateway_application_id.forget_abi(),
                    operator: Some(Self::chain_owner_account(&blob_gateway_creator_chain)),
                },
                vec![],
            )
            .await;

        blob_gateway_creator_chain
            .add_block(|block| {
                block.with_operation(
                    blob_gateway_application_id,
                    BlobGatewayOperation::AppendState {
                        state_application_id: state_application_id.forget_abi(),
                    },
                );
            })
            .await;
        blob_gateway_creator_chain.handle_received_messages().await;

        Self {
            blob_gateway_creator_chain,
            user_chain,
            blob_gateway_application_id,
            state_application_id,
            blob_gateway_bytecode_id,
        }
    }

    async fn deploy_upgrade_application(&mut self) -> ApplicationId<BlobGatewayAbi> {
        self.blob_gateway_creator_chain
            .create_application::<BlobGatewayAbi, (), ()>(
                self.blob_gateway_bytecode_id.clone(),
                (),
                (),
                vec![],
            )
            .await
    }

    async fn append_state_to(&self, application_id: ApplicationId<BlobGatewayAbi>) {
        self.blob_gateway_creator_chain
            .add_block(|block| {
                block.with_operation(
                    application_id,
                    BlobGatewayOperation::AppendState {
                        state_application_id: self.state_application_id.forget_abi(),
                    },
                );
            })
            .await;
        self.blob_gateway_creator_chain
            .handle_received_messages()
            .await;
    }

    async fn handoff(&self, new_application_id: ApplicationId<BlobGatewayAbi>) {
        self.blob_gateway_creator_chain
            .add_block(|block| {
                block.with_operation(
                    self.blob_gateway_application_id,
                    BlobGatewayOperation::Handoff {
                        new_business_application_id: new_application_id.forget_abi(),
                    },
                );
            })
            .await;
        self.blob_gateway_creator_chain
            .handle_received_messages()
            .await;
    }

    async fn register_blob(&self, blob_hash: CryptoHash) {
        self.user_chain
            .add_block(|block| {
                block.with_operation(
                    self.blob_gateway_application_id,
                    BlobGatewayOperation::Register {
                        store_type: StoreType::S3,
                        data_type: BlobDataType::Image,
                        blob_hash,
                    },
                );
            })
            .await;
        self.blob_gateway_creator_chain
            .handle_received_messages()
            .await;
    }

    async fn blobs(&self) -> Vec<BlobData> {
        self.blobs_on(self.blob_gateway_application_id).await
    }

    async fn blobs_on(&self, app_id: ApplicationId<BlobGatewayAbi>) -> Vec<BlobData> {
        let response = self
            .blob_gateway_creator_chain
            .graphql_query(
                app_id,
                Request::new("{ blobs { blobHash storeType dataType creator createdAt } }"),
            )
            .await;
        let data = response.response;
        serde_json::from_value(data.get("blobs").unwrap().clone()).unwrap()
    }

    fn chain_owner_account(chain: &ActiveChain) -> Account {
        Account {
            chain_id: chain.id(),
            owner: AccountOwner::from(chain.public_key()),
        }
    }

    fn user_account(&self) -> Account {
        Self::chain_owner_account(&self.user_chain)
    }

    fn blob_hash(seed: &str) -> CryptoHash {
        CryptoHash::new(&TestString::new(seed.to_string()))
    }
}

#[tokio::test(flavor = "multi_thread")]
async fn state_application_service_is_queryable() {
    let suite = TestSuite::new().await;

    let state_response = suite
        .blob_gateway_creator_chain
        .graphql_query(
            suite.state_application_id,
            Request::new("{ businessApplicationId }"),
        )
        .await;
    let state_data = state_response.response;
    let business_id: ApplicationId =
        serde_json::from_value(state_data.get("businessApplicationId").unwrap().clone()).unwrap();
    assert_eq!(business_id, suite.blob_gateway_application_id.forget_abi());
}

#[tokio::test(flavor = "multi_thread")]
async fn state_application_blobs_query_works_directly() {
    let suite = TestSuite::new().await;
    let blob_hash = TestSuite::blob_hash("blob-direct");

    suite.register_blob(blob_hash).await;

    let state_response = suite
        .blob_gateway_creator_chain
        .graphql_query(
            suite.state_application_id,
            Request::new("{ blobs { blobHash storeType dataType creator createdAt } }"),
        )
        .await;
    let state_data = state_response.response;
    let blobs: Vec<BlobData> =
        serde_json::from_value(state_data.get("blobs").unwrap().clone()).unwrap();
    assert_eq!(blobs.len(), 1);
    assert_eq!(blobs[0].blob_hash, blob_hash);
}

#[tokio::test(flavor = "multi_thread")]
async fn multi_chain_register_and_query_blob_uses_state_application() {
    let suite = TestSuite::new().await;
    let blob_hash = TestSuite::blob_hash("blob-1");

    suite.register_blob(blob_hash).await;

    let version_response = suite
        .blob_gateway_creator_chain
        .graphql_query(
            suite.blob_gateway_application_id,
            Request::new("{ latestStateVersion }"),
        )
        .await;
    let data = version_response.response;
    let version: u16 =
        serde_json::from_value(data.get("latestStateVersion").unwrap().clone()).unwrap();
    assert_eq!(version, 1);

    let blobs = suite.blobs().await;
    assert_eq!(blobs.len(), 1);
    assert_eq!(blobs[0].blob_hash, blob_hash);
    assert_eq!(blobs[0].store_type, StoreType::S3);
    assert_eq!(blobs[0].data_type, BlobDataType::Image);
    assert_eq!(blobs[0].creator, suite.user_account());
}

#[tokio::test(flavor = "multi_thread")]
async fn upgrade_without_new_state_allows_v2_to_read_old_blobs() {
    let mut suite = TestSuite::new().await;
    let blob_hash = TestSuite::blob_hash("blob-2");

    suite.register_blob(blob_hash).await;

    let v2_app_id = suite.deploy_upgrade_application().await;
    suite.append_state_to(v2_app_id).await;
    suite.handoff(v2_app_id).await;

    let blobs = suite.blobs_on(v2_app_id).await;
    assert_eq!(blobs.len(), 1);
    assert_eq!(blobs[0].blob_hash, blob_hash);
}

#[tokio::test(flavor = "multi_thread")]
#[should_panic(expected = "Failed to execute block")]
async fn upgrade_without_new_state_rejects_v1_writes_after_handoff() {
    let mut suite = TestSuite::new().await;
    let blob_hash = TestSuite::blob_hash("blob-3");

    suite.register_blob(blob_hash).await;

    let v2_app_id = suite.deploy_upgrade_application().await;
    suite.append_state_to(v2_app_id).await;
    suite.handoff(v2_app_id).await;

    suite.register_blob(TestSuite::blob_hash("blob-4")).await;
}
