use linera_sdk::linera_base_types::{ApplicationId, ChainId};

pub trait MemeRuntimeContext {
    type Error: std::fmt::Debug + std::error::Error + 'static;

    fn token_creator_chain_id(&mut self, token: ApplicationId) -> Result<ChainId, Self::Error>;
}
