use async_trait::async_trait;
use linera_sdk::linera_base_types::{Account, ApplicationId};

#[async_trait(?Send)]
pub trait PublicStateBaseInterface {
    type Error: std::fmt::Debug + std::error::Error + 'static;
    type BootstrapArgument;

    async fn append_state(
        &mut self,
        state_application_id: ApplicationId,
    ) -> Result<(), Self::Error>;

    async fn bootstrap(&mut self, argument: Self::BootstrapArgument) -> Result<(), Self::Error>;

    async fn handoff(
        &mut self,
        new_business_application_id: ApplicationId,
    ) -> Result<(), Self::Error>;

    async fn set_operator(&mut self, new_operator: Account) -> Result<(), Self::Error>;
}

#[async_trait(?Send)]
pub trait LocalStateInterface {
    type Error: std::fmt::Debug + std::error::Error + 'static;

    async fn append_state(
        &mut self,
        state_application_id: ApplicationId,
    ) -> Result<(), Self::Error>;

    async fn state_application(&self, version: u16) -> Result<ApplicationId, Self::Error>;

    async fn latest_state_application(&self) -> Result<ApplicationId, Self::Error>;

    async fn state_applications(&self) -> Result<Vec<(u16, ApplicationId)>, Self::Error>;
}
