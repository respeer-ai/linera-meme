use abi::ams::{abi::Metadata, state_v1::StateInstantiationArgument};
use async_trait::async_trait;
use linera_sdk::linera_base_types::{Account, ApplicationId};

#[async_trait(?Send)]
pub trait StateInterface {
    type Error: std::fmt::Debug + std::error::Error + 'static;

    fn instantiate(&mut self, argument: StateInstantiationArgument);

    async fn business_application_id(&mut self) -> Result<ApplicationId, Self::Error>;

    async fn handoff(
        &mut self,
        new_business_application_id: ApplicationId,
    ) -> Result<(), Self::Error>;

    async fn operator(&mut self) -> Result<Account, Self::Error>;

    async fn set_operator(&mut self, new_operator: Account) -> Result<(), Self::Error>;

    async fn add_application_type(&mut self, application_type: String) -> Result<(), Self::Error>;

    async fn application_types(&mut self) -> Result<Vec<String>, Self::Error>;

    async fn register_application(&mut self, metadata: Metadata) -> Result<(), Self::Error>;

    async fn claim_application(
        &mut self,
        application_id: ApplicationId,
        creator: Account,
    ) -> Result<(), Self::Error>;

    async fn update_application(
        &mut self,
        application_id: ApplicationId,
        metadata: Metadata,
    ) -> Result<(), Self::Error>;

    async fn application(
        &mut self,
        application_id: ApplicationId,
    ) -> Result<Option<Metadata>, Self::Error>;
}
