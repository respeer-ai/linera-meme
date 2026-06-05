pub mod contract_inner;
pub mod interfaces;
pub mod state;

pub use abi::swap::pool::FundType;
use abi::swap::pool::PoolError as _PoolError;
use async_graphql::SimpleObject;
use linera_sdk::{
    linera_base_types::{Amount, ArithmeticError},
    views::ViewError,
};
use serde::{Deserialize, Serialize};
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

#[derive(Debug, Clone, Deserialize, Serialize, SimpleObject)]
#[serde(rename_all = "camelCase")]
pub struct LiquidityAmount {
    pub liquidity: Amount,
    pub amount_0: Amount,
    pub amount_1: Amount,
}
