use thiserror::Error;

/// An error that can occur during the contract execution.
#[derive(Debug, Error)]
pub enum StateError {
    #[error("View error")]
    ViewError(#[from] linera_sdk::views::ViewError),

    #[error("Already exists")]
    AlreadyExists,

    #[error("Not exists")]
    NotExists,

    #[error("Invalid application type")]
    InvalidApplicationType,

    #[error("Permission denied")]
    PermissionDenied,
}
