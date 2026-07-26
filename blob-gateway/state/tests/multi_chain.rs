#![cfg(not(target_arch = "wasm32"))]

use abi::{
    blob_gateway::{
        state_v1::{BlobGatewayStateAbi, BlobGatewayStateV1Operation, StateInstantiationArgument},
        BlobData, BlobDataType,
    },
    store_type::StoreType,
};
use linera_sdk::{
    linera_base_types::{Account, AccountOwner, ApplicationId, CryptoHash, TestString, Timestamp},
    test::{ActiveChain, TestValidator},
};
use std::str::FromStr;

struct TestSuite {
    state_creator_chain: ActiveChain,
    user_chain: ActiveChain,
    state_application_id: ApplicationId<BlobGatewayStateAbi>,
}

impl TestSuite {
    async fn new() -> Self {
        let (validator, state_bytecode_id) = TestValidator::with_current_module::<
            BlobGatewayStateAbi,
            (),
            StateInstantiationArgument,
        >()
        .await;
        let mut state_creator_chain = validator.new_chain().await;
        let user_chain = validator.new_chain().await;

        let state_application_id = state_creator_chain
            .create_application::<BlobGatewayStateAbi, (), StateInstantiationArgument>(
                state_bytecode_id,
                (),
                StateInstantiationArgument {
                    business_application_id: Self::business_application_id(),
                    operator: None,
                },
                vec![],
            )
            .await;

        Self {
            state_creator_chain,
            user_chain,
            state_application_id,
        }
    }

    async fn routed_message_count_from_user_chain(
        &self,
        operation: BlobGatewayStateV1Operation,
    ) -> usize {
        let (certificate, _) = self
            .user_chain
            .add_block(|block| {
                block.with_operation(self.state_application_id, operation);
            })
            .await;

        certificate
            .message_bundles_for(self.state_creator_chain.id())
            .map(|(_, bundle)| bundle.messages.len())
            .sum()
    }

    async fn assert_user_chain_write_is_rejected(&self, operation: BlobGatewayStateV1Operation) {
        let result = self
            .user_chain
            .try_add_block(|block| {
                block.with_operation(self.state_application_id, operation);
            })
            .await;
        assert!(result.is_err());
    }

    fn blob_data(blob_hash: CryptoHash) -> BlobData {
        BlobData {
            store_type: StoreType::S3,
            data_type: BlobDataType::Image,
            blob_hash,
            creator: Self::chain_owner_account_placeholder(),
            created_at: Timestamp::from(1),
        }
    }

    fn chain_owner_account_placeholder() -> Account {
        Account {
            chain_id: linera_sdk::linera_base_types::ChainId(
                CryptoHash::from_str(
                    "a10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5baa",
                )
                .unwrap(),
            ),
            owner: AccountOwner::from_str(
                "0x02e900512d2fca22897f80a2f6932ff454f2752ef7afad18729dd25e5b5b6e00",
            )
            .unwrap(),
        }
    }

    fn business_application_id() -> ApplicationId {
        Self::application_id("b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bad")
    }

    fn new_business_application_id() -> ApplicationId {
        Self::application_id("b20ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bad")
    }

    fn tracked_blob_hash() -> CryptoHash {
        CryptoHash::new(&TestString::new("blob-1".to_string()))
    }

    fn application_id(value: &str) -> ApplicationId {
        ApplicationId::from_str(value).unwrap()
    }
}

#[tokio::test(flavor = "multi_thread")]
async fn blob_read_from_user_chain_does_not_route_to_state_creator_chain() {
    let suite = TestSuite::new().await;

    assert_eq!(
        suite
            .routed_message_count_from_user_chain(BlobGatewayStateV1Operation::Blob {
                blob_hash: TestSuite::tracked_blob_hash(),
            })
            .await,
        0
    );
}

#[tokio::test(flavor = "multi_thread")]
async fn blobs_read_from_user_chain_does_not_route_to_state_creator_chain() {
    let suite = TestSuite::new().await;

    assert_eq!(
        suite
            .routed_message_count_from_user_chain(BlobGatewayStateV1Operation::Blobs)
            .await,
        0
    );
}

#[tokio::test(flavor = "multi_thread")]
async fn write_operations_from_user_chain_are_rejected_without_business_app_caller() {
    let suite = TestSuite::new().await;

    for operation in [
        BlobGatewayStateV1Operation::CreateBlob {
            blob_data: TestSuite::blob_data(TestSuite::tracked_blob_hash()),
        },
        BlobGatewayStateV1Operation::Handoff {
            new_business_application_id: TestSuite::new_business_application_id(),
        },
    ] {
        suite.assert_user_chain_write_is_rejected(operation).await;
    }
}
