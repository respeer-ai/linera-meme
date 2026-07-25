use abi::blob_gateway::BlobData;
use async_trait::async_trait;
use linera_sdk::linera_base_types::CryptoHash;

#[async_trait(?Send)]
pub trait StateInterface {
    type Error: std::fmt::Debug + std::error::Error + 'static;

    async fn create_blob(&mut self, blob_data: BlobData) -> Result<(), Self::Error>;

    async fn blob(&mut self, blob_hash: CryptoHash) -> Result<Option<BlobData>, Self::Error>;

    async fn blobs(&mut self) -> Result<Vec<BlobData>, Self::Error>;
}
