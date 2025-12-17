use crate::interfaces::state::StateInterface;
use crate::state::{errors::StateError, BlobGatewayState};
use abi::blob_gateway::BlobData;
use async_trait::async_trait;

#[async_trait(?Send)]
impl StateInterface for BlobGatewayState {
    type Error = StateError;

    async fn create_blob(&mut self, blob_data: BlobData) -> Result<(), StateError> {
        let blob_hash = blob_data.blob_hash;

        if self.blobs.contains_key(&blob_hash).await? {
            return Ok(());
        }

        self.blobs.insert(&blob_hash, blob_data)?;

        Ok(())
    }
}
