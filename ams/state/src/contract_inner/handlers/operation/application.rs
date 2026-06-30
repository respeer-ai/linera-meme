use abi::ams::state_v1::{AmsStateOperation, AmsStateResponse};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::ApplicationId;

use crate::interfaces::state::StateInterface;

pub struct ApplicationHandler<S: StateInterface> {
    state: S,
    application_id: ApplicationId,
}

impl<S: StateInterface> ApplicationHandler<S> {
    pub fn new(state: S, operation: &AmsStateOperation) -> Self {
        let AmsStateOperation::Application { application_id } = operation else {
            panic!("Invalid operation");
        };
        Self {
            state,
            application_id: *application_id,
        }
    }
}

#[async_trait(?Send)]
impl<S: StateInterface> Handler<(), AmsStateResponse> for ApplicationHandler<S> {
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<(), AmsStateResponse>>, HandlerError> {
        let application = self
            .state
            .application(self.application_id)
            .await
            .map_err(|error| HandlerError::ProcessError(error.into()))?;

        let mut outcome = HandlerOutcome::new();
        outcome.with_response(AmsStateResponse::Application(application));
        Ok(Some(outcome))
    }
}
