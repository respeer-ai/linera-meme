use async_trait::async_trait;
use linera_sdk::linera_base_types::{Account, ApplicationId};

#[async_trait(?Send)]
pub trait StateInterface {
    type Error: std::fmt::Debug + std::error::Error + 'static;

    async fn initialize_operator(&mut self) -> Result<(), Self::Error>;

    async fn create_namespace(&mut self, namespace: u8) -> Result<(), Self::Error>;

    async fn freeze_namespace(&mut self) -> Result<(), Self::Error>;

    async fn unfreeze_namespace(&mut self) -> Result<(), Self::Error>;

    async fn handoff(
        &mut self,
        namespace: u8,
        new_application_id: ApplicationId,
    ) -> Result<(), Self::Error>;

    async fn set_operator(&mut self, new_operator: Account) -> Result<(), Self::Error>;

    async fn batch_read(
        &mut self,
        namespace: u8,
        keys: Vec<Vec<u8>>,
    ) -> Result<Vec<Option<Vec<u8>>>, Self::Error>;

    async fn batch_write(
        &mut self,
        namespace: u8,
        writes: Vec<(Vec<u8>, Option<Vec<u8>>)>,
    ) -> Result<(), Self::Error>;
}
