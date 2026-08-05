use abi::blob_gateway::{state_v1::StateInstantiationArgument, BlobData};
use async_trait::async_trait;
use linera_sdk::linera_base_types::{Account, ApplicationId, CryptoHash};

use crate::{
    interfaces::state::StateInterface,
    state::{errors::StateError, BlobGatewayStateV1},
};

#[async_trait(?Send)]
impl StateInterface for BlobGatewayStateV1 {
    type Error = StateError;

    fn instantiate(&mut self, argument: StateInstantiationArgument) {
        self.business_application_id
            .set(Some(argument.business_application_id));
        self.operator.set(argument.operator);
    }

    async fn business_application_id(&mut self) -> Result<ApplicationId, Self::Error> {
        self.business_application_id
            .get()
            .ok_or(StateError::BusinessApplicationIdNotInitialized)
    }

    async fn set_operator(&mut self, new_operator: Account) -> Result<(), Self::Error> {
        self.operator.set(Some(new_operator));
        Ok(())
    }

    async fn handoff(
        &mut self,
        new_business_application_id: ApplicationId,
    ) -> Result<(), Self::Error> {
        self.business_application_id
            .set(Some(new_business_application_id));
        Ok(())
    }

    async fn create_blob(&mut self, blob_data: BlobData) -> Result<(), Self::Error> {
        let blob_hash = blob_data.blob_hash;

        if self.blobs.contains_key(&blob_hash).await? {
            return Ok(());
        }

        self.blobs.insert(&blob_hash, blob_data)?;

        Ok(())
    }

    async fn blob(&mut self, blob_hash: CryptoHash) -> Result<Option<BlobData>, Self::Error> {
        Ok(self.blobs.get(&blob_hash).await?)
    }

    async fn blobs(&mut self) -> Result<Vec<BlobData>, Self::Error> {
        Ok(self
            .blobs
            .index_values()
            .await?
            .into_iter()
            .map(|(_, blob_data)| blob_data)
            .collect())
    }
}
