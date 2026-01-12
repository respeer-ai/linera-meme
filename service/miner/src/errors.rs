use linera_core::client::ChainClientError;
use thiserror::Error;

/// An error that can occur during the contract execution.
#[derive(Debug, Error)]
pub enum MemeMinerError {
    #[error(transparent)]
    ChainClientError(#[from] ChainClientError),

    #[error("Not implemented")]
    NotImplemented,

    #[error(transparent)]
    ClientError(#[from] linera_client::Error),

    #[error(transparent)]
    JsonError(#[from] serde_json::error::Error),
}
