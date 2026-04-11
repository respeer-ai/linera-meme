use crate::interfaces::state::StateInterface;
use crate::state::{errors::StateError, AmsState};
use abi::ams::{InstantiationArgument, Metadata, APPLICATION_TYPES};
use async_trait::async_trait;
use linera_sdk::{linera_base_types::{Account, ApplicationId}, util::BlockingWait};

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
        if !self
            .application_types
            .elements()
            .blocking_wait()
            .unwrap()
            .contains(&application.application_type)
        {
            return Err(StateError::InvalidApplicationType);
        }
        let application_id = application.application_id;
        if self
            .applications
            .contains_key(&application_id)
            .blocking_wait()
            .unwrap()
        {
            return Err(StateError::AlreadyExists);
        }
        Ok(self.applications.insert(&application_id, application)?)
    }

    async fn claim_application(
        &mut self,
        owner: Account,
        application_id: ApplicationId,
    ) -> Result<(), StateError> {
        let Some(mut application) = self.applications.get(&application_id).await? else {
            return Err(StateError::NotExists);
        };
        if application.creator.owner != owner.owner {
            return Err(StateError::PermissionDenied);
        }
        application.creator = owner;
        Ok(self.applications.insert(&application_id, application)?)
    }

    async fn update_application(
        &mut self,
        owner: Account,
        application_id: ApplicationId,
        metadata: Metadata,
    ) -> Result<(), StateError> {
        let Some(existing) = self.applications.get(&application_id).await? else {
            return Err(StateError::NotExists);
        };
        if existing.creator.owner != owner.owner {
            return Err(StateError::PermissionDenied);
        }
        if metadata.application_id != application_id {
            return Err(StateError::PermissionDenied);
        }
        if !self
            .application_types
            .elements()
            .await?
            .contains(&metadata.application_type)
        {
            return Err(StateError::InvalidApplicationType);
        }

        let mut updated = metadata;
        updated.creator = existing.creator;
        updated.application_id = existing.application_id;
        updated.created_at = existing.created_at;
        Ok(self.applications.insert(&application_id, updated)?)
    }
}
