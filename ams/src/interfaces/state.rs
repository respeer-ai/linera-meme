use abi::ams::{InstantiationArgument, Metadata};
use async_trait::async_trait;
use linera_sdk::linera_base_types::{Account, ApplicationId};

#[async_trait(?Send)]
pub trait StateInterface {
    type Error: std::fmt::Debug + std::error::Error + 'static;

    fn instantiate(&mut self, owner: Account, argument: InstantiationArgument);

    async fn add_application_type(
        &mut self,
        owner: Account,
        application_type: String,
    ) -> Result<(), Self::Error>;

    fn register_application(&mut self, application: Metadata) -> Result<(), Self::Error>;

    async fn claim_application(
        &mut self,
        owner: Account,
        application_id: ApplicationId,
    ) -> Result<(), Self::Error>;

    async fn update_application(
        &mut self,
        owner: Account,
        application_id: ApplicationId,
        metadata: Metadata,
    ) -> Result<(), Self::Error>;
}
