use linera_sdk::linera_base_types::{ChainId, Timestamp};

pub trait BaseRuntimeContext {
    fn chain_id(&mut self) -> ChainId;
    fn system_time(&mut self) -> Timestamp;
    fn application_creator_chain_id(&mut self) -> ChainId;
}
