use base::handler::HandlerError;
use thiserror::Error;

/// An error that can occur during the contract execution.
#[derive(Debug, Error)]
pub enum StateError {
    #[error(transparent)]
    ViewError(#[from] linera_sdk::views::ViewError),

    #[error("Not exists")]
    NotExists,
}

impl From<StateError> for HandlerError {
    fn from(e: StateError) -> Self {
        HandlerError::ProcessError(e.into())
    }
}
