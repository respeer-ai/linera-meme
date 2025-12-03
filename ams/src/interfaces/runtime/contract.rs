use super::base::BaseRuntimeContext;
use crate::abi::Message;
use linera_sdk::linera_base_types::{AccountOwner, ChainId};

pub trait ContractRuntimeContext: BaseRuntimeContext {
    type Error;

    fn authenticated_signer(&mut self) -> Option<AccountOwner>;
    fn require_authenticated_signer(&mut self) -> Result<AccountOwner, Self::Error>;

    fn send_message(&mut self, destionation: ChainId, message: Message);

    fn message_origin_chain_id(&mut self) -> Option<ChainId>;
    fn require_message_origin_chain_id(&mut self) -> Result<ChainId, Self::Error>;
}
