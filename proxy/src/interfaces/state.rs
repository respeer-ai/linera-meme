use abi::{
    approval::Approval,
    proxy::{InstantiationArgument, Miner},
};
use async_trait::async_trait;
use base::handler::HandlerError;
use linera_sdk::linera_base_types::{
    Account, AccountOwner, ApplicationId, ChainId, ModuleId, Timestamp,
};

#[async_trait(?Send)]
pub trait StateInterface {
    type Error: std::fmt::Debug + std::error::Error + Into<HandlerError> + 'static;

    async fn instantiate(
        &mut self,
        argument: InstantiationArgument,
        owners: Vec<Account>,
    ) -> Result<(), Self::Error>;

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

    // Owner is approved operator, operator is voter
    async fn approve_add_operator(
        &mut self,
        owner: Account,
        operator: Account,
    ) -> Result<(), Self::Error>;

    async fn ban_operator(&mut self, owner: Account) -> Result<(), Self::Error>;

    // Owner is approved operator, operator is voter
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

    fn swap_application_id(&self) -> ApplicationId;

    fn create_chain(&mut self, chain_id: ChainId, timestamp: Timestamp) -> Result<(), Self::Error>;

    async fn create_chain_token(
        &mut self,
        chain_id: ChainId,
        token: ApplicationId,
    ) -> Result<(), Self::Error>;

    async fn register_miner(&mut self, owner: Account, now: Timestamp) -> Result<(), Self::Error>;

    fn deregister_miner(&mut self, owner: Account) -> Result<(), Self::Error>;

    async fn get_miner_with_account_owner(&self, owner: AccountOwner)
        -> Result<Miner, Self::Error>;
}
