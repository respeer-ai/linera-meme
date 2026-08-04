use thiserror::Error;

#[derive(Debug, Error)]
pub enum StateError {
    #[error(transparent)]
    ViewError(#[from] linera_sdk::views::ViewError),

    #[error("Business application id not initialized")]
    BusinessApplicationIdNotInitialized,

    #[error("Operator not initialized")]
    OperatorNotInitialized,

    #[error("Owner not initialized")]
    OwnerNotInitialized,

    #[error("Invalid amount")]
    InvalidAmount,

    #[error("Self transfer")]
    SelfTransfer,

    #[error("Insufficient funds")]
    InsufficientFunds,

    #[error("Balance overflow")]
    BalanceOverflow,

    #[error("Insufficient allowance")]
    InsufficientAllowance,

    #[error("Invalid owner")]
    InvalidOwner,

    #[error("Mining info not initialized")]
    MiningInfoNotInitialized,

    #[error("Already initialized")]
    AlreadyInitialized,

    #[error("Not exists")]
    NotExists,
}
