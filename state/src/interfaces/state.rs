use async_trait::async_trait;
use linera_sdk::linera_base_types::{Account, ApplicationId};

use crate::state_key::StateKey;

#[async_trait(?Send)]
pub trait StateInterface {
    type Error: std::fmt::Debug + std::error::Error + 'static;

    async fn initialize_operator(&mut self, operator: Account) -> Result<(), Self::Error>;
    async fn operator(&mut self) -> Result<Account, Self::Error>;

    async fn create_namespace(
        &mut self,
        namespace: u8,
        application_id: ApplicationId,
    ) -> Result<(), Self::Error>;

    async fn freeze_namespace(&mut self) -> Result<(), Self::Error>;

    async fn unfreeze_namespace(&mut self) -> Result<(), Self::Error>;

    async fn handoff(
        &mut self,
        namespace: u8,
        application_id: ApplicationId,
        new_application_id: ApplicationId,
    ) -> Result<(), Self::Error>;

    async fn set_operator(&mut self, new_operator: Account) -> Result<(), Self::Error>;

    async fn application_slot(
        &mut self,
        namespace: u8,
        application_id: ApplicationId,
    ) -> Result<u8, Self::Error>;

    async fn read(&mut self, key: StateKey) -> Result<Option<Vec<u8>>, Self::Error>;

    async fn write(&mut self, key: StateKey, value: Vec<u8>) -> Result<(), Self::Error>;

    async fn delete(&mut self, key: StateKey) -> Result<(), Self::Error>;

    async fn batch_read(
        &mut self,
        keys: Vec<StateKey>,
    ) -> Result<Vec<Option<Vec<u8>>>, Self::Error>;

    async fn batch_write(&mut self, writes: Vec<(StateKey, Vec<u8>)>) -> Result<(), Self::Error>;

    async fn batch_delete(&mut self, keys: Vec<StateKey>) -> Result<(), Self::Error>;
}
