// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0
//
use abi::swap::transaction::Transaction as PoolTransaction;
use async_graphql::SimpleObject;
use linera_sdk::{
    linera_base_types::{ApplicationId, ArithmeticError, ChangeApplicationPermissionsError},
    views::ViewError,
};
use serde::{Deserialize, Serialize};
use thiserror::Error;

#[derive(Debug, Clone, Deserialize, Serialize, Eq, PartialEq, SimpleObject)]
pub struct TransactionExt {
    pub token_0: ApplicationId,
    pub token_1: Option<ApplicationId>,
    pub transaction: PoolTransaction,
}

#[derive(Debug, Error)]
#[allow(dead_code)]
pub enum SwapError {
    #[error(transparent)]
    ViewError(#[from] ViewError),

    #[error(transparent)]
    ChangeApplicationPermissionsError(#[from] ChangeApplicationPermissionsError),

    #[error(transparent)]
    ArithmeticError(#[from] ArithmeticError),
}
