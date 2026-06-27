use crate::state::{errors::StateError, AmsState};
use abi::application_base_state::StateApplicationIdStorage;
use linera_sdk::linera_base_types::ApplicationId;

impl StateApplicationIdStorage for AmsState {
    type Error = StateError;

    fn set_state_application_id(&mut self, state_application_id: ApplicationId) {
        self.state_app_id.set(Some(state_application_id));
    }

    fn get_state_application_id(&self) -> Result<ApplicationId, StateError> {
        self.state_app_id.get().ok_or(StateError::NotExists)
    }
}
