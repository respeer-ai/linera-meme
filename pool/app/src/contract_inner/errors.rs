use base::handler::HandlerError;
use thiserror::Error;

#[derive(Debug, Error)]
pub enum ContractError {
    #[error(transparent)]
    HandlerError(#[from] HandlerError),
}
