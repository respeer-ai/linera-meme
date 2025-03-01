// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

/*! ABI of the LiquidityRfq Application */

use linera_sdk::views::ViewError;
use thiserror::Error;

#[derive(Debug, Error)]
#[allow(dead_code)]
pub enum LiquidityRfqError {
    #[error(transparent)]
    ViewError(#[from] ViewError),
}
