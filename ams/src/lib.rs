use thiserror::Error;

#[derive(Debug, Error)]
#[allow(dead_code)]
pub enum AmsError {
    #[error(transparent)]
    ViewError(#[from] linera_sdk::views::ViewError),

    #[error("Permission denied")]
    PermissionDenied,

    #[error("Not implemented")]
    NotImplemented,
}
