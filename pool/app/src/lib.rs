pub mod contract_inner;
pub mod interfaces;
pub mod state;

pub use abi::pool::FundType;
pub use abi::pool::LiquidityAmount;
use abi::pool::PoolError as _PoolError;
use linera_sdk::{linera_base_types::ArithmeticError, views::ViewError};
use thiserror::Error;

#[derive(Debug, Error)]
#[allow(dead_code)]
pub enum PoolError {
    #[error(transparent)]
    ViewError(#[from] ViewError),

    #[error(transparent)]
    PoolError(#[from] _PoolError),

    #[error(transparent)]
    ArithmeticError(#[from] ArithmeticError),

    #[error("Invalid amount")]
    InvalidAmount,

    #[error("Insufficient funds")]
    InsufficientFunds,
}
