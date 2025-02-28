// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0
//
use linera_sdk::views::ViewError;
use thiserror::Error;

#[derive(Debug, Error)]
#[allow(dead_code)]
pub enum SwapError {
    #[error(transparent)]
    ViewError(#[from] ViewError),
}
