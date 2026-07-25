use abi::blob_gateway::state_v1::{BlobGatewayStateV1Operation, BlobGatewayStateV1Response};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::CryptoHash;

use crate::interfaces::state::StateInterface;

pub struct BlobHandler<S: StateInterface> {
    state: S,
    blob_hash: CryptoHash,
}

impl<S: StateInterface> BlobHandler<S> {
    pub fn new(state: S, operation: &BlobGatewayStateV1Operation) -> Self {
        let BlobGatewayStateV1Operation::Blob { blob_hash } = operation else {
            panic!("Invalid operation");
        };
        Self {
            state,
            blob_hash: *blob_hash,
        }
    }
}

#[async_trait(?Send)]
impl<S: StateInterface> Handler<(), BlobGatewayStateV1Response> for BlobHandler<S> {
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<(), BlobGatewayStateV1Response>>, HandlerError> {
        let blob = self
            .state
            .blob(self.blob_hash)
            .await
            .map_err(|error| HandlerError::ProcessError(error.into()))?;

        let mut outcome = HandlerOutcome::new();
        outcome.with_response(BlobGatewayStateV1Response::Blob(blob));
        Ok(Some(outcome))
    }
}
