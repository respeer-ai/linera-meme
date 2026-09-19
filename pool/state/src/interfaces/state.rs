use abi::pool::state_v1::StateInstantiationArgument;
use abi::pool::{Pool, Transaction};
use async_trait::async_trait;
use linera_sdk::linera_base_types::{Account, Amount, ApplicationId};

#[async_trait(?Send)]
pub trait StateInterface {
    type Error: std::fmt::Debug + std::error::Error + 'static;

    fn instantiate(&mut self, argument: StateInstantiationArgument) -> Result<(), Self::Error>;

    async fn business_application_id(&mut self) -> Result<ApplicationId, Self::Error>;

    async fn handoff(
        &mut self,
        new_business_application_id: ApplicationId,
    ) -> Result<(), Self::Error>;

    async fn operator(&mut self) -> Result<Account, Self::Error>;

    async fn set_operator(&mut self, new_operator: Account) -> Result<(), Self::Error>;

    async fn initialize(
        &mut self,
        pool: Pool,
        router_application_id: ApplicationId,
    ) -> Result<(), Self::Error>;

    async fn set_pool(&mut self, pool: Pool) -> Result<(), Self::Error>;

    async fn pool(&self) -> Result<Pool, Self::Error>;

    async fn router_application_id(&self) -> Result<ApplicationId, Self::Error>;

    async fn total_supply(&self) -> Result<Amount, Self::Error>;

    async fn mint_shares(&mut self, to: Account, amount: Amount) -> Result<(), Self::Error>;

    async fn burn_shares(&mut self, from: Account, amount: Amount) -> Result<(), Self::Error>;

    async fn liquidity(&self, account: Account) -> Result<Amount, Self::Error>;

    async fn claimable_balance(
        &self,
        token: Option<ApplicationId>,
        owner: Account,
    ) -> Result<Amount, Self::Error>;

    async fn claiming_balance(
        &self,
        token: Option<ApplicationId>,
        owner: Account,
    ) -> Result<Amount, Self::Error>;

    async fn credit_claimable(
        &mut self,
        token: Option<ApplicationId>,
        owner: Account,
        amount: Amount,
    ) -> Result<(), Self::Error>;

    async fn debit_claimable(
        &mut self,
        token: Option<ApplicationId>,
        owner: Account,
        amount: Amount,
    ) -> Result<(), Self::Error>;

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

    async fn set_fee_to(&mut self, operator: Account, account: Account) -> Result<(), Self::Error>;

    async fn set_fee_to_setter(
        &mut self,
        operator: Account,
        account: Account,
    ) -> Result<(), Self::Error>;

    async fn build_transaction(
        &mut self,
        transaction: Transaction,
    ) -> Result<Transaction, Self::Error>;
}
