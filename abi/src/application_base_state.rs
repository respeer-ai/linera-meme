use linera_sdk::linera_base_types::ApplicationId;

pub trait StateApplicationIdStorage {
    type Error: std::fmt::Debug + std::error::Error + 'static;

    fn set_state_application_id(&mut self, state_application_id: ApplicationId);

    fn get_state_application_id(&self) -> Result<ApplicationId, Self::Error>;
}
