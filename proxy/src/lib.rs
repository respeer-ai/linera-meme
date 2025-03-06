// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

use linera_sdk::linera_base_types::{ArithmeticError, ChangeApplicationPermissionsError};
use linera_views::views::ViewError;
use thiserror::Error;

#[derive(Debug, Error)]
#[allow(dead_code)]
pub enum ProxyError {
    #[error(transparent)]
    ViewError(#[from] ViewError),

    #[error(transparent)]
    ArithmeticError(#[from] ArithmeticError),

    #[error("Not exists")]
    NotExists,

    #[error(transparent)]
    ChangeApplicationPermissionsError(#[from] ChangeApplicationPermissionsError),
}
