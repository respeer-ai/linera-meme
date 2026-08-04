use abi::meme::{HandoffArgument, InitializeArgument, Liquidity, MiningInfo};
use async_trait::async_trait;
use linera_sdk::linera_base_types::{Account, Amount, ApplicationId};

#[async_trait(?Send)]
pub trait StateInterface {
    type Error: std::fmt::Debug + std::error::Error + 'static;

    async fn owner(&self) -> Result<Account, Self::Error>;

    async fn transfer(
        &mut self,
        origin: Account,
        to: Account,
        amount: Amount,
    ) -> Result<(), Self::Error>;

    async fn transfer_from(
        &mut self,
        origin: Account,
        from: Account,
        to: Account,
        amount: Amount,
    ) -> Result<(), Self::Error>;

    async fn approve(
        &mut self,
        origin: Account,
        spender: Account,
        amount: Amount,
    ) -> Result<(), Self::Error>;

    async fn mint(&mut self, to: Account, amount: Amount) -> Result<(), Self::Error>;

    async fn transfer_ownership(
        &mut self,
        owner: Account,
        new_owner: Account,
    ) -> Result<(), Self::Error>;

    async fn redeem(
        &mut self,
        from: Account,
        to: Account,
        amount: Option<Amount>,
    ) -> Result<(), Self::Error>;

    async fn transfer_from_application(
        &mut self,
        from: Account,
        to: Account,
        amount: Amount,
    ) -> Result<(), Self::Error>;

    async fn mining_info(&self) -> Result<MiningInfo, Self::Error>;

    async fn mining_reward(
        &mut self,
        owner: Account,
        reward_amount: Amount,
        mining_info: MiningInfo,
    ) -> Result<(), Self::Error>;

    async fn balance_of(&self, owner: Account) -> Result<Amount, Self::Error>;

    async fn allowance_of(&self, owner: Account, spender: Account) -> Result<Amount, Self::Error>;

    async fn swap_application_id(&self) -> Result<Option<ApplicationId>, Self::Error>;

    async fn proxy_application_id(&self) -> Result<Option<ApplicationId>, Self::Error>;

    async fn start_mining(&mut self) -> Result<(), Self::Error>;

    async fn initialize(&mut self, argument: InitializeArgument) -> Result<(), Self::Error>;

    async fn initial_liquidity(&self) -> Result<Option<Liquidity>, Self::Error>;

    async fn handoff(&mut self, argument: HandoffArgument) -> Result<(), Self::Error>;
}
