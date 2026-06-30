use abi::ams::{
    abi::{Metadata, APPLICATION_TYPES},
    state_v1::StateInstantiationArgument,
};
use async_trait::async_trait;
use linera_sdk::linera_base_types::{Account, ApplicationId};

use crate::{
    interfaces::state::StateInterface,
    state::{errors::StateError, AmsState},
};

#[async_trait(?Send)]
impl StateInterface for AmsState {
    type Error = StateError;

    fn instantiate(&mut self, argument: StateInstantiationArgument) {
        self.business_application_id
            .set(Some(argument.business_application_id));
        self.operator.set(argument.operator);
        self.application_types.set(
            APPLICATION_TYPES
                .iter()
                .map(|application_type| application_type.to_string())
                .collect(),
        );
    }

    async fn business_application_id(&mut self) -> Result<ApplicationId, Self::Error> {
        self.business_application_id
            .get()
            .ok_or(StateError::BusinessApplicationIdNotInitialized)
    }

    async fn handoff(
        &mut self,
        new_business_application_id: ApplicationId,
    ) -> Result<(), Self::Error> {
        self.business_application_id
            .set(Some(new_business_application_id));
        Ok(())
    }

    async fn operator(&mut self) -> Result<Account, Self::Error> {
        self.operator
            .get()
            .ok_or(StateError::OperatorNotInitialized)
    }

    async fn set_operator(&mut self, new_operator: Account) -> Result<(), Self::Error> {
        self.operator.set(Some(new_operator));
        Ok(())
    }

    async fn add_application_type(&mut self, application_type: String) -> Result<(), Self::Error> {
        let mut application_types = self.application_types.get().clone();
        if application_types.contains(&application_type) {
            return Err(StateError::ApplicationTypeAlreadyExists);
        }
        application_types.push(application_type);
        self.application_types.set(application_types);
        Ok(())
    }

    async fn application_types(&mut self) -> Result<Vec<String>, Self::Error> {
        Ok(self.application_types.get().clone())
    }

    async fn register_application(&mut self, metadata: Metadata) -> Result<(), Self::Error> {
        let application_id = metadata.application_id;
        if self.applications.contains_key(&application_id).await? {
            return Err(StateError::ApplicationAlreadyExists);
        }
        self.applications.insert(&application_id, metadata)?;
        Ok(())
    }

    async fn claim_application(
        &mut self,
        application_id: ApplicationId,
        creator: Account,
    ) -> Result<(), Self::Error> {
        let mut metadata = self
            .applications
            .get(&application_id)
            .await?
            .ok_or(StateError::ApplicationNotFound)?;
        metadata.creator = creator;
        self.applications.insert(&application_id, metadata)?;
        Ok(())
    }

    async fn update_application(
        &mut self,
        application_id: ApplicationId,
        metadata: Metadata,
    ) -> Result<(), Self::Error> {
        if !self.applications.contains_key(&application_id).await? {
            return Err(StateError::ApplicationNotFound);
        }
        self.applications.insert(&application_id, metadata)?;
        Ok(())
    }

    async fn application(
        &mut self,
        application_id: ApplicationId,
    ) -> Result<Option<Metadata>, Self::Error> {
        Ok(self.applications.get(&application_id).await?)
    }
}
