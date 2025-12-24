use linera_sdk::linera_base_types::AccountPermissionError;
use thiserror::Error;

#[derive(Debug, Error)]
pub enum RuntimeError {
    #[error(transparent)]
    RuntimeAccountPermissionError(#[from] AccountPermissionError),

    #[error("Invalid message origin chain id")]
    InvalidMessageOriginChainId,

    #[error("Invalid authenticated signer")]
    InvalidAuthenticatedSigner,

    #[error("Invalid authenticated caller")]
    InvalidAuthenticatedCaller,

    #[error("Permission denied: {0}")]
    PermissionDenied(String),

    #[error("Invalid application response")]
    InvalidApplicationResponse,
}
