use thiserror::Error;

#[derive(Debug, Error)]
pub enum StateError {
    #[error("Invalid state response")]
    InvalidStateResponse,

    #[error("Invalid state version")]
    InvalidStateVersion,

    #[error("Business application id not initialized")]
    BusinessApplicationIdNotInitialized,

    #[error("Operator not initialized")]
    OperatorNotInitialized,

    #[error("Not exists")]
    NotExists,

    #[error("View error: {0}")]
    View(#[from] linera_sdk::views::ViewError),

    #[error("State already initialized")]
    AlreadyInitialized,
}
