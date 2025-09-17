use abi::ams::{Metadata, APPLICATION_TYPES};
use ams::AmsError;
use async_graphql::SimpleObject;
use linera_sdk::{
    linera_base_types::{Account, ApplicationId},
    views::{linera_views, MapView, QueueView, RegisterView, RootView, ViewStorageContext},
};

#[derive(RootView, SimpleObject)]
#[view(context = ViewStorageContext)]
pub struct AmsState {
    pub application_types: QueueView<String>,
    pub applications: MapView<ApplicationId, Metadata>,
    pub operator: RegisterView<Option<Account>>,
    pub subscribed_creator_chain: RegisterView<bool>,
}

#[allow(dead_code)]
impl AmsState {
    pub(crate) async fn instantiate(&mut self, owner: Account) {
        self.operator.set(Some(owner));
        for application_type in APPLICATION_TYPES {
            self.application_types
                .push_back(application_type.to_string());
        }
    }

    pub(crate) async fn add_application_type(
        &mut self,
        owner: Account,
        application_type: String,
    ) -> Result<(), AmsError> {
        if self.operator.get().unwrap() != owner {
            return Err(AmsError::PermissionDenied);
        }
        if self
            .application_types
            .elements()
            .await?
            .contains(&application_type)
        {
            return Err(AmsError::AlreadyExists);
        }
        self.application_types.push_back(application_type);
        Ok(())
    }

    pub(crate) async fn register_application(
        &mut self,
        application: Metadata,
    ) -> Result<(), AmsError> {
        let application_id = application.application_id;
        Ok(self.applications.insert(&application_id, application)?)
    }
}
