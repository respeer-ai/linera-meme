use std::sync::Arc;

use crate::state::AmsState;
use abi::{
    ams::{AmsKey, Metadata},
    application_base_state::StateApplicationIdStorage,
    namespace,
};
use linera_sdk::{linera_base_types::ApplicationId, Service, ServiceRuntime};
use state::{adapters::service::StateServiceAdapter, interfaces::service::StateServiceInterface};

use super::StateError;

pub struct ServiceStateAdapter<S: Service> {
    state_service: StateServiceAdapter<S>,
}

impl<S: Service> ServiceStateAdapter<S> {
    pub fn new(runtime: Arc<ServiceRuntime<S>>, state: Arc<AmsState>) -> Result<Self, StateError> {
        let state_application_id = state.get_state_application_id()?;
        Ok(Self {
            state_service: StateServiceAdapter::new(runtime, state_application_id, namespace::AMS),
        })
    }

    pub fn application(
        &self,
        application_id: ApplicationId,
    ) -> Result<Option<Metadata>, StateError> {
        Ok(self
            .state_service
            .read(&AmsKey::Application { application_id })?)
    }

    pub fn applications(&self) -> Result<Vec<Metadata>, StateError> {
        let application_ids = self
            .state_service
            .read::<_, Vec<ApplicationId>>(&AmsKey::ApplicationIds)?
            .unwrap_or_default();
        // Batch-read only `AmsKey::Application` records here. Other `AmsKey` variants
        // store different value types and must be read with separate typed `read` calls.
        let keys = application_ids
            .into_iter()
            .map(|application_id| AmsKey::Application { application_id })
            .collect::<Vec<_>>();
        Ok(self
            .state_service
            .batch_read::<_, Metadata>(&keys)?
            .into_iter()
            .flatten()
            .collect())
    }
}
