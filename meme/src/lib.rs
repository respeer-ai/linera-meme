// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

use linera_sdk::{linera_base_types::ArithmeticError, views::ViewError};
use thiserror::Error;

#[derive(Debug, Error)]
#[allow(dead_code)]
pub enum MemeError {
    #[error(transparent)]
    ViewError(#[from] ViewError),

    #[error(transparent)]
    ArithmeticError(#[from] ArithmeticError),

    #[error("Inconsistent balance")]
    InconsistentBalance,

    #[error("Insufficient funds")]
    InsufficientFunds,

    #[error("Invalid owner")]
    InvalidOwner,

    #[error("Invalid amount")]
    InvalidAmount,

    #[error("Self transfer")]
    SelfTransfer,
}
