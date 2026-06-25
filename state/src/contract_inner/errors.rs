use thiserror::Error;

#[derive(Debug, Error)]
pub enum ContractInnerError {
    #[error("state contract handler is not implemented yet")]
    NotImplemented,
}
