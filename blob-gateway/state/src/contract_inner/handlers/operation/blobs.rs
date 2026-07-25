use abi::blob_gateway::state_v1::BlobGatewayStateV1Response;
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};

use crate::interfaces::state::StateInterface;

pub struct BlobsHandler<S: StateInterface> {
    state: S,
}

impl<S: StateInterface> BlobsHandler<S> {
    pub fn new(state: S) -> Self {
        Self { state }
    }
}

#[async_trait(?Send)]
impl<S: StateInterface> Handler<(), BlobGatewayStateV1Response> for BlobsHandler<S> {
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<(), BlobGatewayStateV1Response>>, HandlerError> {
        let blobs = self
            .state
            .blobs()
            .await
            .map_err(|error| HandlerError::ProcessError(error.into()))?;

        let mut outcome = HandlerOutcome::new();
        outcome.with_response(BlobGatewayStateV1Response::Blobs(blobs));
        Ok(Some(outcome))
    }
}
