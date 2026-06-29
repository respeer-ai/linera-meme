use std::sync::Arc;

use crate::state::AmsState;
use abi::{
    ams::{abi::Metadata, state_v1::AmsStateAbi as AmsStateV1Abi},
    application_state_base::{decode_response_field, LocalStateInterface},
};
use async_graphql::{Request, Variables};
use linera_sdk::{linera_base_types::ApplicationId, serde_json::json, Service, ServiceRuntime};

use super::StateError;

enum AmsQuery {
    Application { application_id: ApplicationId },
    Applications,
}

impl AmsQuery {
    const APPLICATION_FIELD: &'static str = "application";
    const APPLICATIONS_FIELD: &'static str = "applications";

    fn request(&self) -> Request {
        match self {
            Self::Application { application_id } => Request::new(
                "query($applicationId: ApplicationId!) { application(applicationId: $applicationId) }",
            )
            .variables(Variables::from_json(json!({
                "applicationId": application_id,
            }))),
            Self::Applications => Request::new("query { applications }"),
        }
    }
}

pub struct ServiceStateAdapter<S: Service> {
    runtime: Arc<ServiceRuntime<S>>,
    state: Arc<AmsState>,
}

impl<S: Service> ServiceStateAdapter<S> {
    pub fn new(runtime: Arc<ServiceRuntime<S>>, state: Arc<AmsState>) -> Result<Self, StateError> {
        Ok(Self { runtime, state })
    }

    pub async fn application(
        &self,
        application_id: ApplicationId,
    ) -> Result<Option<Metadata>, StateError> {
        let query = AmsQuery::Application { application_id };
        let state_application_id = self.state.latest_state_application().await?;
        Ok(decode_response_field(
            self.runtime.query_application(
                state_application_id.with_abi::<AmsStateV1Abi>(),
                &query.request(),
            ),
            AmsQuery::APPLICATION_FIELD,
        )?)
    }

    pub async fn applications(&self) -> Result<Vec<Metadata>, StateError> {
        let query = AmsQuery::Applications;
        let state_application_id = self.state.latest_state_application().await?;
        Ok(decode_response_field(
            self.runtime.query_application(
                state_application_id.with_abi::<AmsStateV1Abi>(),
                &query.request(),
            ),
            AmsQuery::APPLICATIONS_FIELD,
        )?)
    }
}
