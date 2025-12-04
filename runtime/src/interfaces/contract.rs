use super::base::BaseRuntimeContext;
use linera_sdk::linera_base_types::{Account, AccountOwner, ChainId};

pub trait ContractRuntimeContext: BaseRuntimeContext {
    type Error;
    type Message;

    fn authenticated_account(&mut self) -> Account;
    fn authenticated_signer(&mut self) -> Option<AccountOwner>;
    fn require_authenticated_signer(&mut self) -> Result<AccountOwner, Self::Error>;

    fn send_message(&mut self, destionation: ChainId, message: Self::Message);

    fn message_origin_chain_id(&mut self) -> Option<ChainId>;
    fn require_message_origin_chain_id(&mut self) -> Result<ChainId, Self::Error>;
}
