use abi::pool::{Pool, Transaction};
use async_trait::async_trait;
use linera_sdk::linera_base_types::{Account, Amount, ApplicationId};

#[async_trait(?Send)]
pub trait StateInterface {
    type Error: std::fmt::Debug + std::error::Error + 'static;

    async fn initialize(
        &mut self,
        pool: Pool,
        router_application_id: ApplicationId,
    ) -> Result<(), Self::Error>;

    async fn set_fee_to(
        &mut self,
        operator: Account,
        account: Account,
    ) -> Result<(), Self::Error>;

    async fn set_fee_to_setter(
        &mut self,
        operator: Account,
        account: Account,
    ) -> Result<(), Self::Error>;

    async fn pool(&self) -> Result<Pool, Self::Error>;

    async fn router_application_id(&self) -> Result<ApplicationId, Self::Error>;

    async fn claim(
        &mut self,
        token: Option<ApplicationId>,
        owner: Account,
        amount: Amount,
    ) -> Result<(), Self::Error>;

    async fn claim_success(
        &mut self,
        token: Option<ApplicationId>,
        owner: Account,
        amount: Amount,
    ) -> Result<(), Self::Error>;

    async fn claim_fail(
        &mut self,
        token: Option<ApplicationId>,
        owner: Account,
        amount: Amount,
    ) -> Result<(), Self::Error>;

    async fn credit_claimable(
        &mut self,
        token: Option<ApplicationId>,
        owner: Account,
        amount: Amount,
    ) -> Result<(), Self::Error>;

    async fn total_supply(&self) -> Result<Amount, Self::Error>;

    async fn mint_shares(&mut self, to: Account, amount: Amount) -> Result<(), Self::Error>;

    async fn burn_shares(&mut self, from: Account, amount: Amount) -> Result<(), Self::Error>;

    async fn set_pool(&mut self, pool: Pool) -> Result<(), Self::Error>;

    async fn build_transaction(
        &mut self,
        transaction: Transaction,
    ) -> Result<Transaction, Self::Error>;
}
