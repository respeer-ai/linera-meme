// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

use async_graphql::{Request, Response};
use linera_sdk::{
    base::{AccountOwner, Amount, ContractAbi, CryptoHash, Owner, ServiceAbi},
    graphql::GraphQLMutationRoot,
};
use serde::{Deserialize, Serialize};

pub struct SwapAbi;

impl ContractAbi for SwapAbi {
    type Operation = SwapOperation;
    type Response = SwapResponse;
}

impl ServiceAbi for SwapAbi {
    type Query = Request;
    type QueryResponse = Response;
}

#[derive(Debug, Deserialize, Serialize, GraphQLMutationRoot)]
pub enum SwapOperation {
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

#[derive(Debug, Deserialize, Serialize, Default)]
pub enum SwapResponse {
    #[default]
    Ok,
}
