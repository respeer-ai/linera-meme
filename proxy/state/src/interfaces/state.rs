use abi::{
    approval::Approval,
    proxy::{state_v1::StateInstantiationArgument, Chain, InitializeArgument, Miner},
};
use async_trait::async_trait;
use linera_sdk::linera_base_types::{
    Account, AccountOwner, ApplicationId, ChainId, ModuleId, Timestamp,
};

#[async_trait(?Send)]
pub trait StateInterface {
    type Error: std::fmt::Debug + std::error::Error + 'static;

    fn instantiate(&mut self, argument: StateInstantiationArgument) -> Result<(), Self::Error>;

    async fn initialize(&mut self, argument: InitializeArgument) -> Result<(), Self::Error>;

    async fn business_application_id(&mut self) -> Result<ApplicationId, Self::Error>;

    async fn handoff(
        &mut self,
        new_business_application_id: ApplicationId,
    ) -> Result<(), Self::Error>;

    async fn operator(&mut self) -> Result<Account, Self::Error>;

    async fn set_operator(&mut self, new_operator: Account) -> Result<(), Self::Error>;

    async fn initial_approval(&self) -> Result<Approval, Self::Error>;

    async fn add_genesis_miner(&mut self, owner: Account) -> Result<(), Self::Error>;

    async fn approve_add_genesis_miner(
        &mut self,
        owner: Account,
        operator: Account,
    ) -> Result<(), Self::Error>;

    async fn genesis_miners(&self) -> Result<Vec<Miner>, Self::Error>;

    async fn is_genesis_miner(&self, owner: Account) -> Result<bool, Self::Error>;

    async fn genesis_miner_owners(&self) -> Result<Vec<AccountOwner>, Self::Error>;

    async fn miners(&self) -> Result<Vec<Miner>, Self::Error>;

    async fn miner_owners(&self) -> Result<Vec<AccountOwner>, Self::Error>;

    async fn validate_operator(&self, owner: Account) -> Result<(), Self::Error>;

    async fn add_operator(&mut self, owner: Account) -> Result<(), Self::Error>;

    async fn approve_add_operator(
        &mut self,
        owner: Account,
        operator: Account,
    ) -> Result<(), Self::Error>;

    async fn ban_operator(&mut self, owner: Account) -> Result<(), Self::Error>;

    async fn approve_ban_operator(
        &mut self,
        owner: Account,
        operator: Account,
    ) -> Result<(), Self::Error>;

    async fn remove_genesis_miner(&mut self, owner: Account) -> Result<(), Self::Error>;

    async fn approve_remove_genesis_miner(
        &mut self,
        owner: Account,
        operator: Account,
    ) -> Result<(), Self::Error>;

    fn meme_bytecode_id(&self) -> ModuleId;

    async fn set_meme_bytecode_ids(
        &mut self,
        business_bytecode_id: ModuleId,
        state_bytecode_id: ModuleId,
    ) -> Result<(), Self::Error>;

    async fn meme_state_bytecode_ids(&self) -> Result<Vec<(u16, ModuleId)>, Self::Error>;

    fn swap_application_id(&self) -> ApplicationId;

    fn create_chain(&mut self, chain_id: ChainId, timestamp: Timestamp) -> Result<(), Self::Error>;

    async fn create_chain_token(
        &mut self,
        chain_id: ChainId,
        token: ApplicationId,
    ) -> Result<(), Self::Error>;

    async fn register_miner(&mut self, owner: Account, now: Timestamp) -> Result<(), Self::Error>;

    async fn deregister_miner(&mut self, owner: Account) -> Result<(), Self::Error>;

    async fn get_miner_with_account_owner(&self, owner: AccountOwner)
        -> Result<Miner, Self::Error>;

    async fn chain(&self, chain_id: ChainId) -> Result<Option<Chain>, Self::Error>;

    async fn chains(&self, created_after: Option<Timestamp>) -> Result<Vec<Chain>, Self::Error>;

    async fn chain_by_token(&self, token: ApplicationId) -> Result<Option<Chain>, Self::Error>;
}
