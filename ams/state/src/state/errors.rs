use thiserror::Error;

#[derive(Debug, Error)]
pub enum StateError {
    #[error(transparent)]
    ViewError(#[from] linera_sdk::views::ViewError),

    #[error("business application id is not initialized")]
    BusinessApplicationIdNotInitialized,

    #[error("operator is not initialized")]
    OperatorNotInitialized,

    #[error("application type already exists")]
    ApplicationTypeAlreadyExists,

    #[error("application already exists")]
    ApplicationAlreadyExists,

    #[error("application does not exist")]
    ApplicationNotFound,
}
