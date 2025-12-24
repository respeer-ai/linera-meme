use abi::swap::{InstantiationArgument, Metadata, router::Pool, transaction::Transaction};
use async_trait::async_trait;
use linera_sdk::linera_base_types::{Account, Amount, ApplicationId, Timestamp, ModuleId, ChainId};

#[async_trait(?Send)]
pub trait StateInterface {
    type Error: std::fmt::Debug + std::error::Error + 'static;

    fn instantiate(&mut self, owner: Account, argument: InstantiationArgument);

    async fn get_pool(
        &self,
        token_0: ApplicationId,
        token_1: Option<ApplicationId>,
    ) -> Result<Option<Pool>, Self::Error>;

    async fn get_pool_exchangable(
        &self,
        token_0: ApplicationId,
        token_1: Option<ApplicationId>,
    ) -> Result<Option<Pool>, Self::Error>;

    fn pool_bytecode_id(&self) -> ModuleId;

    async fn create_pool(
        &mut self,
        creator: Account,
        token_0: ApplicationId,
        token_1: Option<ApplicationId>,
        pool_application: Account,
        timestamp: Timestamp,
    ) -> Result<(), Self::Error>;

    fn create_pool_chain(&mut self, chain_id: ChainId) -> Result<(), Self::Error>;

    async fn update_pool(
        &mut self,
        token_0: ApplicationId,
        token_1: Option<ApplicationId>,
        transaction: Transaction,
        token_0_price: Amount,
        token_1_price: Amount,
        reserve_0: Amount,
        reserve_1: Amount,
    ) -> Result<(), Self::Error>;
}
