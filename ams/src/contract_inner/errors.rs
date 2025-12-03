use super::handlers::errors::HandlerError;
use thiserror::Error;

#[derive(Debug, Error)]
pub enum ContractError {
    #[error(transparent)]
    HandlerError(#[from] HandlerError),
}
