#![cfg(not(target_arch = "wasm32"))]

use abi::{
    ams::{AmsAbi, AmsOperation, InstantiationArgument, Metadata},
    state::StateAbi,
    store_type::StoreType,
};
use async_graphql::Request;
use linera_sdk::{
    linera_base_types::{Account, AccountOwner, ApplicationId, CryptoHash, TestString, Timestamp},
    test::{ActiveChain, TestValidator},
};
use std::str::FromStr;

struct TestSuite {
    ams_creator_chain: ActiveChain,
    user_chain: ActiveChain,
    same_owner_chain: ActiveChain,
    ams_application_id: ApplicationId<AmsAbi>,
}

impl TestSuite {
    async fn new() -> Self {
        let (validator, ams_bytecode_id) =
            TestValidator::with_current_module::<AmsAbi, (), InstantiationArgument>().await;
        let mut state_creator_chain = validator.new_chain().await;
        let mut ams_creator_chain = validator.new_chain().await;
        let user_chain = validator.new_chain().await;
        let same_owner_chain = validator
            .new_chain_with_keypair(user_chain.key_pair().copy())
            .await;
        let state_bytecode_id = state_creator_chain
            .publish_bytecode_files_in("../../state")
            .await;
        let state_application_id = state_creator_chain
            .create_application::<StateAbi, (), ()>(state_bytecode_id, (), (), vec![])
            .await;
        let ams_application_id = ams_creator_chain
            .create_application::<AmsAbi, (), InstantiationArgument>(
                ams_bytecode_id,
                (),
                InstantiationArgument {
                    state_app_id: state_application_id.forget_abi(),
                },
                vec![state_application_id.forget_abi()],
            )
            .await;

        Self {
            ams_creator_chain,
            user_chain,
            same_owner_chain,
            ams_application_id,
        }
    }

    async fn add_application_type(&self, application_type: &str) {
        self.ams_creator_chain
            .add_block(|block| {
                block.with_operation(
                    self.ams_application_id,
                    AmsOperation::AddApplicationType {
                        application_type: application_type.to_string(),
                    },
                );
            })
            .await;
        self.ams_creator_chain.handle_received_messages().await;
    }

    async fn register_application(&self, metadata: Metadata) {
        self.user_chain
            .add_block(|block| {
                block.with_operation(self.ams_application_id, AmsOperation::Register { metadata });
            })
            .await;
        self.ams_creator_chain.handle_received_messages().await;
    }

    async fn claim_application(&self, chain: &ActiveChain, application_id: ApplicationId) {
        chain
            .add_block(|block| {
                block.with_operation(
                    self.ams_application_id,
                    AmsOperation::Claim { application_id },
                );
            })
            .await;
        self.ams_creator_chain.handle_received_messages().await;
    }

    async fn update_application(
        &self,
        chain: &ActiveChain,
        application_id: ApplicationId,
        metadata: Metadata,
    ) {
        chain
            .add_block(|block| {
                block.with_operation(
                    self.ams_application_id,
                    AmsOperation::Update {
                        application_id,
                        metadata,
                    },
                );
            })
            .await;
        self.ams_creator_chain.handle_received_messages().await;
    }

    async fn application(&self, application_id: ApplicationId) -> Option<Metadata> {
        let response = self
            .ams_creator_chain
            .graphql_query(
                self.ams_application_id,
                Request::new(format!(
                    "{{ application(applicationId: \"{}\") }}",
                    application_id
                )),
            )
            .await;
        let data = response.response;
        serde_json::from_value(data.get("application").unwrap().clone()).unwrap()
    }

    async fn applications(&self) -> Vec<Metadata> {
        let response = self
            .ams_creator_chain
            .graphql_query(
                self.ams_application_id,
                Request::new("{ applications(limit: 20) }"),
            )
            .await;
        let data = response.response;
        serde_json::from_value(data.get("applications").unwrap().clone()).unwrap()
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

    fn same_owner_account(&self) -> Account {
        Account {
            chain_id: self.same_owner_chain.id(),
            owner: self.user_account().owner,
        }
    }

    fn metadata(&self, application_id: ApplicationId, application_type: &str) -> Metadata {
        Metadata {
            creator: self.user_account(),
            application_name: "Test App".to_string(),
            application_id,
            application_type: application_type.to_string(),
            key_words: vec!["test".to_string()],
            logo_store_type: StoreType::S3,
            logo: CryptoHash::new(&TestString::new("logo".to_string())),
            description: "First description".to_string(),
            twitter: None,
            telegram: None,
            discord: None,
            website: None,
            github: None,
            spec: None,
            created_at: Timestamp::from(0),
        }
    }

    fn application_id(value: &str) -> ApplicationId {
        ApplicationId::from_str(value).unwrap()
    }
}

#[tokio::test(flavor = "multi_thread")]
async fn multi_chain_register_add_type_claim_and_update_use_state_application() {
    let suite = TestSuite::new().await;
    let first_application_id = TestSuite::application_id(
        "b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bae",
    );
    let second_application_id = TestSuite::application_id(
        "c10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bae",
    );

    suite.add_application_type("Analytics").await;
    suite
        .register_application(suite.metadata(first_application_id, "Analytics"))
        .await;
    suite
        .register_application(suite.metadata(second_application_id, "Meme"))
        .await;

    let registered = suite.application(first_application_id).await.unwrap();
    assert_eq!(registered.application_type, "Analytics");
    assert_eq!(registered.creator, suite.user_account());
    assert_eq!(suite.applications().await.len(), 2);

    suite
        .claim_application(&suite.same_owner_chain, first_application_id)
        .await;
    let claimed = suite.application(first_application_id).await.unwrap();
    assert_eq!(claimed.creator, suite.same_owner_account());

    let mut updated = claimed.clone();
    updated.application_name = "Updated App".to_string();
    updated.description = "Updated description".to_string();
    updated.application_type = "Game".to_string();
    updated.key_words = vec!["updated".to_string()];
    suite
        .update_application(&suite.same_owner_chain, first_application_id, updated)
        .await;

    let stored = suite.application(first_application_id).await.unwrap();
    assert_eq!(stored.application_name, "Updated App");
    assert_eq!(stored.description, "Updated description");
    assert_eq!(stored.application_type, "Game");
    assert_eq!(stored.key_words, vec!["updated".to_string()]);
    assert_eq!(stored.creator, suite.same_owner_account());
}
