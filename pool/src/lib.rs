// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

/*! ABI of the Pool Example Application */

use abi::swap::pool::PoolError as _PoolError;
use async_graphql::{Enum, SimpleObject};
use linera_sdk::{
    linera_base_types::{Account, Amount, ApplicationId, ArithmeticError, Timestamp},
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
}

#[derive(Clone, Debug, Deserialize, Serialize, Enum, Eq, Copy, PartialEq)]
pub enum FundType {
    Swap,
    AddLiquidity,
}

#[derive(Clone, Debug, Deserialize, Serialize, Enum, Eq, Copy, PartialEq)]
pub enum FundStatus {
    // Fund request is created but not sent
    Created,
    // Fund request is sent but not respond
    InFlight,
    Success,
    Fail,
}

#[derive(Debug, Clone, Deserialize, Serialize, SimpleObject)]
pub struct FundRequest {
    pub from: Account,
    pub token: Option<ApplicationId>,
    pub amount_in: Amount,
    // Swap pair token min out amount
    pub pair_token_amount_out_min: Option<Amount>,
    pub to: Option<Account>,
    pub block_timestamp: Option<Timestamp>,
    pub fund_type: FundType,
    pub status: FundStatus,
    pub error: Option<String>,
    // When add liquidity, we need to transfer two assets
    pub prev_request: Option<u64>,
    pub next_request: Option<u64>,
}

#[derive(Debug, Clone, Deserialize, Serialize, SimpleObject)]
#[serde(rename_all = "camelCase")]
pub struct LiquidityAmount {
    pub liquidity: Amount,
    pub amount_0: Amount,
    pub amount_1: Amount,
}
