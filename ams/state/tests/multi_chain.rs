#![cfg(not(target_arch = "wasm32"))]

use abi::{
    ams::{
        abi::Metadata,
        state_v1::{AmsStateAbi, AmsStateOperation, StateInstantiationArgument},
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
    state_application_id: ApplicationId<AmsStateAbi>,
}

impl TestSuite {
    async fn new() -> Self {
        let (validator, state_bytecode_id) =
            TestValidator::with_current_module::<AmsStateAbi, (), StateInstantiationArgument>()
                .await;
        let mut state_creator_chain = validator.new_chain().await;
        let user_chain = validator.new_chain().await;
        let operator = Self::chain_owner_account(&state_creator_chain);

        let state_application_id = state_creator_chain
            .create_application::<AmsStateAbi, (), StateInstantiationArgument>(
                state_bytecode_id,
                (),
                StateInstantiationArgument {
                    business_application_id: Self::business_application_id(),
                    operator: Some(operator),
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

    async fn routed_message_count_from_user_chain(&self, operation: AmsStateOperation) -> usize {
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

    async fn assert_user_chain_write_is_rejected(&self, operation: AmsStateOperation) {
        let result = self
            .user_chain
            .try_add_block(|block| {
                block.with_operation(self.state_application_id, operation);
            })
            .await;
        assert!(result.is_err());
    }

    fn chain_owner_account(chain: &ActiveChain) -> Account {
        Account {
            chain_id: chain.id(),
            owner: AccountOwner::from(chain.public_key()),
        }
    }

    fn metadata(application_id: ApplicationId, application_type: &str) -> Metadata {
        Metadata {
            creator: Self::chain_owner_account_placeholder(),
            application_name: "Test App".to_string(),
            application_id,
            application_type: application_type.to_string(),
            key_words: vec!["test".to_string()],
            logo_store_type: StoreType::S3,
            logo: CryptoHash::new(&TestString::new("logo".to_string())),
            description: "Test description".to_string(),
            twitter: None,
            telegram: None,
            discord: None,
            website: None,
            github: None,
            spec: None,
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

    fn tracked_application_id() -> ApplicationId {
        Self::application_id("c10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bad")
    }

    fn other_tracked_application_id() -> ApplicationId {
        Self::application_id("c20ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bad")
    }

    fn application_id(value: &str) -> ApplicationId {
        ApplicationId::from_str(value).unwrap()
    }
}

#[tokio::test(flavor = "multi_thread")]
async fn application_read_from_user_chain_does_not_route_to_state_creator_chain() {
    let suite = TestSuite::new().await;

    assert_eq!(
        suite
            .routed_message_count_from_user_chain(AmsStateOperation::Application {
                application_id: TestSuite::tracked_application_id(),
            })
            .await,
        0
    );
}

#[tokio::test(flavor = "multi_thread")]
async fn write_operations_from_user_chain_are_rejected_without_business_app_caller() {
    let suite = TestSuite::new().await;
    let tracked_application_id = TestSuite::tracked_application_id();
    let other_tracked_application_id = TestSuite::other_tracked_application_id();

    for operation in [
        AmsStateOperation::SetOperator {
            new_operator: TestSuite::chain_owner_account(&suite.user_chain),
        },
        AmsStateOperation::AddApplicationType {
            owner: TestSuite::chain_owner_account_placeholder(),
            application_type: "Analytics".to_string(),
        },
        AmsStateOperation::RegisterApplication {
            metadata: TestSuite::metadata(tracked_application_id, "Meme"),
        },
        AmsStateOperation::ClaimApplication {
            owner: TestSuite::chain_owner_account_placeholder(),
            application_id: tracked_application_id,
        },
        AmsStateOperation::UpdateApplication {
            owner: TestSuite::chain_owner_account_placeholder(),
            application_id: tracked_application_id,
            metadata: TestSuite::metadata(other_tracked_application_id, "Game"),
        },
        AmsStateOperation::Handoff {
            new_business_application_id: TestSuite::new_business_application_id(),
        },
    ] {
        suite.assert_user_chain_write_is_rejected(operation).await;
    }
}
