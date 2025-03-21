#![cfg_attr(target_arch = "wasm32", no_main)]

mod state;

use linera_sdk::{
    linera_base_types::{Account, AccountOwner, ApplicationId, WithContractAbi},
    views::{RootView, View},
    Contract, ContractRuntime,
};

use self::state::AmsState;
use abi::ams::{AmsAbi, AmsMessage, AmsOperation, AmsResponse, InstantiationArgument, Metadata};
use ams::AmsError;

pub struct ApplicationContract {
    state: AmsState,
    runtime: ContractRuntime<Self>,
}

linera_sdk::contract!(ApplicationContract);

impl WithContractAbi for ApplicationContract {
    type Abi = AmsAbi;
}

impl Contract for ApplicationContract {
    type Message = AmsMessage;
    type Parameters = ();
    type InstantiationArgument = InstantiationArgument;

    async fn load(runtime: ContractRuntime<Self>) -> Self {
        let state = AmsState::load(runtime.root_view_storage_context())
            .await
            .expect("Failed to load state");
        ApplicationContract { state, runtime }
    }

    async fn instantiate(&mut self, _argument: InstantiationArgument) {
        let owner = Account {
            chain_id: self.runtime.chain_id(),
            owner: Some(AccountOwner::User(
                self.runtime.authenticated_signer().expect("Invalid owner"),
            )),
        };
        self.state.instantiate(owner).await;
    }

    async fn execute_operation(&mut self, operation: AmsOperation) -> AmsResponse {
        match operation {
            AmsOperation::Register { metadata } => self
                .on_op_register(metadata)
                .await
                .expect("Failed OP: register"),
            AmsOperation::Claim { application_id } => self
                .on_op_claim(application_id)
                .await
                .expect("Failed OP: claim"),
            AmsOperation::AddApplicationType { application_type } => self
                .on_op_add_application_type(application_type)
                .await
                .expect("Failed OP: add application type"),
            AmsOperation::Update {
                application_id,
                metadata,
            } => self
                .on_op_update(application_id, metadata)
                .await
                .expect("Failed OP: update"),
        }
    }

    async fn execute_message(&mut self, message: AmsMessage) {
        if self.runtime.chain_id() != self.runtime.application_creator_chain_id() {
            panic!("Messages can only be executed on creator chain");
        }
        match message {
            AmsMessage::Register { metadata } => self
                .on_msg_register(metadata)
                .await
                .expect("Failed MSG: register"),
            AmsMessage::Claim { application_id } => self
                .on_msg_claim(application_id)
                .await
                .expect("Failed MSG: claim"),
            AmsMessage::AddApplicationType {
                owner,
                application_type,
            } => self
                .on_msg_add_application_type(owner, application_type)
                .await
                .expect("Failed MSG: add application type"),
            AmsMessage::Update {
                owner,
                application_id,
                metadata,
            } => self
                .on_msg_update(owner, application_id, metadata)
                .await
                .expect("Failed MSG: update"),
        }
    }

    async fn store(mut self) {
        self.state.save().await.expect("Failed to save state");
    }
}

impl ApplicationContract {
    fn owner_account(&mut self) -> Account {
        Account {
            chain_id: self.runtime.chain_id(),
            owner: match self.runtime.authenticated_signer() {
                Some(owner) => Some(AccountOwner::User(owner)),
                _ => None,
            },
        }
    }

    async fn on_op_register(&mut self, mut metadata: Metadata) -> Result<AmsResponse, AmsError> {
        let creator = self.owner_account();

        metadata.creator = creator;
        metadata.created_at = self.runtime.system_time();

        self.runtime
            .prepare_message(AmsMessage::Register { metadata })
            .with_authentication()
            .send_to(self.runtime.application_creator_chain_id());
        Ok(AmsResponse::Ok)
    }

    async fn on_op_claim(
        &mut self,
        _application_id: ApplicationId,
    ) -> Result<AmsResponse, AmsError> {
        Err(AmsError::NotImplemented)
    }

    async fn on_op_add_application_type(
        &mut self,
        application_type: String,
    ) -> Result<AmsResponse, AmsError> {
        let owner = self.owner_account();
        self.runtime
            .prepare_message(AmsMessage::AddApplicationType {
                owner,
                application_type,
            })
            .with_authentication()
            .send_to(self.runtime.application_creator_chain_id());
        Ok(AmsResponse::Ok)
    }

    async fn on_op_update(
        &self,
        _application_id: ApplicationId,
        _metadata: Metadata,
    ) -> Result<AmsResponse, AmsError> {
        Err(AmsError::NotImplemented)
    }

    async fn on_msg_register(&mut self, metadata: Metadata) -> Result<(), AmsError> {
        self.state.register_application(metadata.clone()).await?;
        Ok(())
    }

    async fn on_msg_claim(&mut self, _application_id: ApplicationId) -> Result<(), AmsError> {
        Err(AmsError::NotImplemented)
    }

    async fn on_msg_add_application_type(
        &mut self,
        owner: Account,
        application_type: String,
    ) -> Result<(), AmsError> {
        self.state
            .add_application_type(owner, application_type.clone())
            .await?;
        Ok(())
    }

    async fn on_msg_update(
        &mut self,
        _owner: Account,
        _application_id: ApplicationId,
        _metadata: Metadata,
    ) -> Result<(), AmsError> {
        Err(AmsError::NotImplemented)
    }
}
