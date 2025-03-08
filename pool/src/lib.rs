// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

/*! ABI of the Pool Example Application */

use linera_sdk::views::ViewError;
use thiserror::Error;

#[derive(Debug, Error)]
#[allow(dead_code)]
pub enum PoolError {
    #[error(transparent)]
    ViewError(#[from] ViewError),
}
