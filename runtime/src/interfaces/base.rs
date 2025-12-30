use linera_sdk::linera_base_types::{
    Account, AccountOwner, Amount, ApplicationId, ChainId, Timestamp,
};
use serde::Serialize;

pub trait BaseRuntimeContext {
    type Parameters: Serialize;

    fn chain_id(&mut self) -> ChainId;
    fn system_time(&mut self) -> Timestamp;
    fn application_creator_chain_id(&mut self) -> ChainId;
    fn application_creation_account(&mut self) -> Account;
    fn application_account(&mut self) -> Account;

    fn application_id(&mut self) -> ApplicationId;

    fn chain_balance(&mut self) -> Amount;
    fn owner_balance(&mut self, owner: AccountOwner) -> Amount;

    fn application_parameters(&mut self) -> Self::Parameters;
}
