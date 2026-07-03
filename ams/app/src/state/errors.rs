use thiserror::Error;

/// An error that can occur during the contract execution.
#[derive(Debug, Error)]
pub enum StateError {
    #[error("View error")]
    ViewError(#[from] linera_sdk::views::ViewError),

    #[error(transparent)]
    ApplicationStateResponse(#[from] abi::application_state_base::ApplicationStateResponseError),

    #[error("Already exists")]
    AlreadyExists,

    #[error("Not exists")]
    NotExists,

    #[error("Invalid state version")]
    InvalidStateVersion,

    #[error("Invalid state response")]
    InvalidStateResponse,
}
