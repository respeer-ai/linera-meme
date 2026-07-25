use crate::state::{errors::StateError, BlobGatewayState, EXPECTED_LATEST_STATE_VERSION};
use abi::application_state_base::LocalStateInterface;
use async_trait::async_trait;
use linera_sdk::linera_base_types::ApplicationId;

#[async_trait]
impl LocalStateInterface for BlobGatewayState {
    type Error = StateError;

    async fn append_state(
        &mut self,
        state_application_id: ApplicationId,
    ) -> Result<(), Self::Error> {
        if self
            .state_applications
            .index_values()
            .await?
            .iter()
            .any(|(_, app_id)| app_id == &state_application_id)
        {
            return Err(StateError::AlreadyExists);
        }
        let next_version = self.latest_state_version.get() + 1;
        if next_version > EXPECTED_LATEST_STATE_VERSION {
            return Err(StateError::InvalidStateVersion);
        }
        if self.state_applications.contains_key(&next_version).await? {
            return Err(StateError::AlreadyExists);
        }
        self.state_applications
            .insert(&next_version, state_application_id)?;
        self.latest_state_version.set(next_version);
        Ok(())
    }

    async fn state_application(&self, version: u16) -> Result<ApplicationId, Self::Error> {
        if version == 0 || version > EXPECTED_LATEST_STATE_VERSION {
            return Err(StateError::InvalidStateVersion);
        }
        self.state_applications
            .get(&version)
            .await?
            .ok_or(StateError::NotExists)
    }

    async fn latest_state_application(&self) -> Result<ApplicationId, Self::Error> {
        let version = *self.latest_state_version.get();
        if version != EXPECTED_LATEST_STATE_VERSION {
            return Err(StateError::InvalidStateVersion);
        }
        self.state_applications
            .get(&version)
            .await?
            .ok_or(StateError::NotExists)
    }

    async fn _state_applications(&self) -> Result<Vec<(u16, ApplicationId)>, Self::Error> {
        Ok(self.state_applications.index_values().await?)
    }
}
