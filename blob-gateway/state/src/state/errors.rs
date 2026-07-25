use thiserror::Error;

#[derive(Debug, Error)]
pub enum StateError {
    #[error(transparent)]
    ViewError(#[from] linera_sdk::views::ViewError),

    #[error("business application id is not initialized")]
    BusinessApplicationIdNotInitialized,
}
