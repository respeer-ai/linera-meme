use async_trait::async_trait;
use linera_sdk::linera_base_types::{Account, ApplicationId};

use crate::{interfaces::state::StateInterface, state::errors::StateError, state::State};

#[async_trait(?Send)]
impl StateInterface for State {
    type Error = StateError;

    async fn initialize_operator(&mut self) -> Result<(), Self::Error> {
        Err(StateError::NotImplemented)
    }

    async fn create_namespace(&mut self, _namespace: u8) -> Result<(), Self::Error> {
        Err(StateError::NotImplemented)
    }

    async fn freeze_namespace(&mut self) -> Result<(), Self::Error> {
        Err(StateError::NotImplemented)
    }

    async fn unfreeze_namespace(&mut self) -> Result<(), Self::Error> {
        Err(StateError::NotImplemented)
    }

    async fn handoff(
        &mut self,
        _namespace: u8,
        _new_application_id: ApplicationId,
    ) -> Result<(), Self::Error> {
        Err(StateError::NotImplemented)
    }

    async fn set_operator(&mut self, _new_operator: Account) -> Result<(), Self::Error> {
        Err(StateError::NotImplemented)
    }

    async fn batch_read(
        &mut self,
        _namespace: u8,
        _keys: Vec<Vec<u8>>,
    ) -> Result<Vec<Option<Vec<u8>>>, Self::Error> {
        Err(StateError::NotImplemented)
    }

    async fn batch_write(
        &mut self,
        _namespace: u8,
        _writes: Vec<(Vec<u8>, Option<Vec<u8>>)>,
    ) -> Result<(), Self::Error> {
        Err(StateError::NotImplemented)
    }
}
