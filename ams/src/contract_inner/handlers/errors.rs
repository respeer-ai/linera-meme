use thiserror::Error;

#[derive(Debug, Error)]
pub enum HandlerError {
    #[error("Invalid operation and message")]
    InvalidOperationAndMessage,

    #[error(transparent)]
    RuntimeError(Box<dyn std::error::Error>),
}
