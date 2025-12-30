use base::handler::HandlerError;
use linera_sdk::{linera_base_types::ArithmeticError, views::ViewError};
use thiserror::Error;

/// An error that can occur during the contract execution.
#[derive(Debug, Error)]
pub enum StateError {
    #[error(transparent)]
    ViewError(#[from] ViewError),

    #[error(transparent)]
    ArithmeticError(#[from] ArithmeticError),

    #[error("Insufficient funds")]
    InsufficientFunds,

    #[error("Invalid owner")]
    InvalidOwner,

    #[error("Invalid amount")]
    InvalidAmount,

    #[error("Self transfer")]
    SelfTransfer,
}

impl From<StateError> for HandlerError {
    fn from(e: StateError) -> Self {
        HandlerError::ProcessError(e.into())
    }
}
