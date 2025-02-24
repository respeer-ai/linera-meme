// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

use async_graphql::{Request, Response};
use linera_sdk::{
    base::{AccountOwner, Amount, ContractAbi, ServiceAbi},
    graphql::GraphQLMutationRoot,
};
use serde::{Deserialize, Serialize};

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
    BalanceOf {
        owner: AccountOwner,
    },
    Mint {
        to: Option<AccountOwner>,
        amount: Amount,
    },
    TransferOwhership {
        new_owner: AccountOwner,
    },
}

#[derive(Debug, Deserialize, Serialize, Default)]
pub enum MemeResponse {
    #[default]
    Ok,
}
