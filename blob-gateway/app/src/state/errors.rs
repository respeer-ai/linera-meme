use abi::application_state_base::ApplicationStateResponseError;
use thiserror::Error;

/// An error that can occur during the contract execution.
#[derive(Debug, Error)]
pub enum StateError {
    #[error("View error")]
    ViewError(#[from] linera_sdk::views::ViewError),

    #[error("invalid state version")]
    InvalidStateVersion,

    #[error("state application already exists")]
    AlreadyExists,

    #[error("state application does not exist")]
    NotExists,

    #[error("invalid state response")]
    InvalidStateResponse,

    #[error("operator not supported")]
    OperatorNotSupported,

    #[error(transparent)]
    ApplicationStateResponseError(#[from] ApplicationStateResponseError),
}
