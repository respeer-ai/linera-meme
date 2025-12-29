use super::base::BaseRuntimeContext;
use linera_sdk::{
    abi::ContractAbi,
    linera_base_types::{
        Account, AccountOwner, Amount, ApplicationId, ApplicationPermissions, ChainId,
        ChainOwnership, ChangeApplicationPermissionsError, ModuleId,
    },
};
use serde::Serialize;

pub trait ContractRuntimeContext: BaseRuntimeContext {
    type Error: std::fmt::Debug + std::error::Error + 'static;
    type Message;

    fn authenticated_account(&mut self) -> Account;
    fn authenticated_signer(&mut self) -> Option<AccountOwner>;
    fn require_authenticated_signer(&mut self) -> Result<AccountOwner, Self::Error>;
    fn authenticated_caller_id(&mut self) -> Option<ApplicationId>;
    fn require_authenticated_caller_id(&mut self) -> Result<ApplicationId, Self::Error>;
    fn owner_accounts(&mut self) -> Vec<Account>;

    fn send_message(&mut self, destionation: ChainId, message: Self::Message);

    fn message_origin_chain_id(&mut self) -> Option<ChainId>;
    fn require_message_origin_chain_id(&mut self) -> Result<ChainId, Self::Error>;
    fn message_signer_account(&mut self) -> Account;

    fn create_application<Abi, Parameters, InstantiationArgument>(
        &mut self,
        module_id: ModuleId,
        parameters: &Parameters,
        argument: &InstantiationArgument,
    ) -> ApplicationId<Abi>
    where
        Abi: ContractAbi,
        Parameters: Serialize,
        InstantiationArgument: Serialize;

    fn call_application<A: ContractAbi + Send>(
        &mut self,
        application: ApplicationId<A>,
        call: &A::Operation,
    ) -> A::Response;

    fn transfer(&mut self, source: AccountOwner, destination: Account, amount: Amount);
    fn transfer_combined(
        &mut self,
        source: Option<AccountOwner>,
        destination: Account,
        amount: Amount,
    );

    fn open_chain(
        &mut self,
        chain_ownership: ChainOwnership,
        application_permissions: ApplicationPermissions,
        balance: Amount,
    ) -> ChainId;
    fn chain_ownership(&mut self) -> ChainOwnership;

    fn change_application_permissions(
        &mut self,
        application_permissions: ApplicationPermissions,
    ) -> Result<(), ChangeApplicationPermissionsError>;
}
