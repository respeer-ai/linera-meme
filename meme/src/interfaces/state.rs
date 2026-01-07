use abi::{
    meme::{InstantiationArgument, Liquidity, Meme, MiningInfo},
    store_type::StoreType,
};
use async_trait::async_trait;
use base::handler::HandlerError;
use linera_sdk::linera_base_types::{
    Account, AccountOwner, Amount, ApplicationId, BlockHeight, ChainId, CryptoHash,
};

#[async_trait(?Send)]
pub trait StateInterface {
    type Error: std::fmt::Debug + std::error::Error + Into<HandlerError> + 'static;

    async fn initialize_liquidity(
        &mut self,
        liquidity: Liquidity,
        swap_creator_chain_id: ChainId,
    ) -> Result<(), Self::Error>;

    fn instantiate(
        &mut self,
        owner: Account,
        application: Account,
        argument: InstantiationArgument,
    ) -> Result<(), Self::Error>;

    async fn mint(&mut self, to: Account, amount: Amount) -> Result<(), Self::Error>;

    fn proxy_application_id(&self) -> Option<ApplicationId>;

    fn blob_gateway_application_id(&self) -> Option<ApplicationId>;

    fn ams_application_id(&self) -> Option<ApplicationId>;

    fn swap_application_id(&self) -> Option<ApplicationId>;

    async fn transfer_(
        &mut self,
        from: Account,
        to: Account,
        amount: Amount,
    ) -> Result<(), Self::Error>;

    async fn transfer(
        &mut self,
        from: Account,
        to: Account,
        amount: Amount,
    ) -> Result<(), Self::Error>;

    async fn transfer_ensure(
        &mut self,
        from: Account,
        to: Account,
        amount: Amount,
    ) -> Result<(), Self::Error>;

    async fn approve(
        &mut self,
        owner: Account,
        spender: Account,
        amount: Amount,
    ) -> Result<(), Self::Error>;

    async fn transfer_from(
        &mut self,
        owner: Account,
        from: Account,
        to: Account,
        amount: Amount,
    ) -> Result<(), Self::Error>;

    fn owner(&self) -> Account;

    fn owner_signer(&self) -> AccountOwner;

    async fn balance_of(&self, owner: Account) -> Amount;

    async fn allowance_of(&self, owner: Account, spender: Account) -> Amount;

    fn initial_owner_balance(&self) -> Amount;

    fn transfer_ownership(&mut self, owner: Account, new_owner: Account)
        -> Result<(), Self::Error>;

    fn name(&self) -> String;

    fn logo_store_type(&self) -> StoreType;

    fn logo(&self) -> CryptoHash;

    fn description(&self) -> String;

    fn twitter(&self) -> Option<String>;

    fn telegram(&self) -> Option<String>;

    fn discord(&self) -> Option<String>;

    fn website(&self) -> Option<String>;

    fn github(&self) -> Option<String>;

    fn meme(&self) -> Meme;

    fn mining_target(&self) -> CryptoHash;

    fn previous_nonce(&self) -> CryptoHash;

    fn mining_height(&self) -> BlockHeight;

    fn mining_info(&self) -> MiningInfo;

    fn update_mining_info(&mut self, info: MiningInfo);
}
