use crate::interfaces::state::StateInterface;
use crate::state::{errors::StateError, AmsState};
use abi::ams::{InstantiationArgument, Metadata, APPLICATION_TYPES};
use async_trait::async_trait;
use linera_sdk::linera_base_types::Account;

#[async_trait(?Send)]
impl StateInterface for AmsState {
    type Error = StateError;

    fn instantiate(&mut self, owner: Account, _argument: InstantiationArgument) {
        self.operator.set(Some(owner));
        for application_type in APPLICATION_TYPES {
            self.application_types
                .push_back(application_type.to_string());
        }
    }

    async fn add_application_type(
        &mut self,
        owner: Account,
        application_type: String,
    ) -> Result<(), StateError> {
        if self.operator.get().unwrap() != owner {
            return Err(StateError::PermissionDenied);
        }
        if self
            .application_types
            .elements()
            .await?
            .contains(&application_type)
        {
            return Err(StateError::AlreadyExists);
        }
        self.application_types.push_back(application_type);
        Ok(())
    }

    fn register_application(&mut self, application: Metadata) -> Result<(), StateError> {
        let application_id = application.application_id;
        Ok(self.applications.insert(&application_id, application)?)
    }
}
