use abi::blob_gateway::BlobData;
use async_trait::async_trait;

#[async_trait(?Send)]
pub trait StateInterface {
    type Error: std::fmt::Debug + std::error::Error + 'static;

    async fn create_blob(&mut self, blob_data: BlobData) -> Result<(), Self::Error>;
}
