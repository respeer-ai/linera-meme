use thiserror::Error;

#[derive(Debug, Error)]
pub enum StateError {
    #[error("state behavior is not implemented yet")]
    NotImplemented,
}
