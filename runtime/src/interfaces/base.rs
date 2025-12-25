use linera_sdk::linera_base_types::{AccountOwner, Amount, ApplicationId, ChainId, Timestamp};

pub trait BaseRuntimeContext {
    fn chain_id(&mut self) -> ChainId;
    fn system_time(&mut self) -> Timestamp;
    fn application_creator_chain_id(&mut self) -> ChainId;

    fn application_id(&mut self) -> ApplicationId;

    fn chain_balance(&mut self) -> Amount;
    fn owner_balance(&mut self, owner: AccountOwner) -> Amount;
}
