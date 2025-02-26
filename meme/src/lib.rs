// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

use async_graphql::{Request, Response};
use linera_sdk::{
    base::{AccountOwner, Amount, ArithmeticError, ContractAbi, CryptoHash, Owner, ServiceAbi},
    graphql::GraphQLMutationRoot,
    views::ViewError,
};
use serde::{Deserialize, Serialize};
use thiserror::Error;

pub struct MemeAbi;

impl ContractAbi for MemeAbi {
    type Operation = MemeOperation;
    type Response = MemeResponse;
}

impl ServiceAbi for MemeAbi {
    type Query = Request;
    type QueryResponse = Response;
}

#[derive(Debug, Deserialize, Serialize, GraphQLMutationRoot)]
pub enum MemeOperation {
    Transfer {
        to: AccountOwner,
        amount: Amount,
    },
    TransferFrom {
        from: AccountOwner,
        to: AccountOwner,
        amount: Amount,
    },
    Approve {
        spender: AccountOwner,
        amount: Amount,
    },
    TransferOwnership {
        new_owner: Owner,
    },
    Mine {
        nonce: CryptoHash,
    },
}

#[derive(Debug, Deserialize, Serialize)]
pub enum MemeMessage {
    Transfer {
        to: AccountOwner,
        amount: Amount,
    },
    TransferFrom {
        from: AccountOwner,
        to: AccountOwner,
        amount: Amount,
    },
    Approve {
        spender: AccountOwner,
        amount: Amount,
    },
    TransferOwnership {
        new_owner: Owner,
    },
    // Mine is only run on creation chain so we don't need a message
}

#[derive(Debug, Deserialize, Serialize, Default)]
pub enum MemeResponse {
    #[default]
    Ok,
}

#[derive(Debug, Error)]
#[allow(dead_code)]
pub enum MemeError {
    #[error(transparent)]
    ViewError(#[from] ViewError),

    #[error(transparent)]
    ArithmeticError(#[from] ArithmeticError),

    #[error("Inconsistent balance")]
    InconsistentBalance,
}
