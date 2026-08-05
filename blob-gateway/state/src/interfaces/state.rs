use abi::blob_gateway::{state_v1::StateInstantiationArgument, BlobData};
use async_trait::async_trait;
use linera_sdk::linera_base_types::{Account, ApplicationId, CryptoHash};

#[async_trait(?Send)]
pub trait StateInterface {
    type Error: std::fmt::Debug + std::error::Error + 'static;

    fn instantiate(&mut self, argument: StateInstantiationArgument);

    async fn business_application_id(&mut self) -> Result<ApplicationId, Self::Error>;

    async fn set_operator(&mut self, new_operator: Account) -> Result<(), Self::Error>;

    async fn handoff(
        &mut self,
        new_business_application_id: ApplicationId,
    ) -> Result<(), Self::Error>;

    async fn create_blob(&mut self, blob_data: BlobData) -> Result<(), Self::Error>;

    async fn blob(&mut self, blob_hash: CryptoHash) -> Result<Option<BlobData>, Self::Error>;

    async fn blobs(&mut self) -> Result<Vec<BlobData>, Self::Error>;
}
