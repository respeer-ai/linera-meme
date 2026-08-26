use base::handler::HandlerError;
use abi::application_state_base::ApplicationStateResponseError;
use thiserror::Error;

/// An error that can occur during the contract execution.
#[derive(Debug, Error)]
pub enum StateError {
    #[error(transparent)]
    ViewError(#[from] linera_sdk::views::ViewError),

    #[error(transparent)]
    ApplicationStateResponse(#[from] ApplicationStateResponseError),

    #[error("Already exists")]
    AlreadyExists,

    #[error("Not exists")]
    NotExists,

    #[error("Invalid state version")]
    InvalidStateVersion,

    #[error("Invalid state response")]
    InvalidStateResponse,
}

impl From<StateError> for HandlerError {
    fn from(e: StateError) -> Self {
        HandlerError::ProcessError(e.into())
    }
}
