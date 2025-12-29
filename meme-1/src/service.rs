// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

#![cfg_attr(target_arch = "wasm32", no_main)]

use std::{str::FromStr, sync::Arc};

use abi::meme::{Meme, MemeAbi, MemeOperation};
use async_graphql::{EmptySubscription, Object, Request, Response, Schema};
use linera_sdk::{
    linera_base_types::{Account, Amount, ChainId, WithServiceAbi},
    views::View,
    Service, ServiceRuntime,
};
use meme::state::MemeState;

pub struct MemeService {
    state: Arc<MemeState>,
    runtime: Arc<ServiceRuntime<Self>>,
}

linera_sdk::service!(MemeService);

impl WithServiceAbi for MemeService {
    type Abi = MemeAbi;
}

impl Service for MemeService {
    type Parameters = ();

    async fn new(runtime: ServiceRuntime<Self>) -> Self {
        let state = MemeState::load(runtime.root_view_storage_context())
            .await
            .expect("Failed to load state");
        MemeService {
            state: Arc::new(state),
            runtime: Arc::new(runtime),
        }
    }

    async fn handle_query(&self, request: Request) -> Response {
        let schema = Schema::build(
            QueryRoot {
                state: self.state.clone(),
                runtime: self.runtime.clone(),
            },
            MutationRoot {
                runtime: self.runtime.clone(),
            },
            EmptySubscription,
        )
        .finish();
        schema.execute(request).await
    }
}

struct QueryRoot {
    state: Arc<MemeState>,
    runtime: Arc<ServiceRuntime<MemeService>>,
}

#[Object]
impl QueryRoot {
    async fn total_supply(&self) -> Amount {
        self.state.meme.get().as_ref().unwrap().total_supply
    }

    // async fn balance_of(&self, owner: Account) -> Amount {
    async fn balance_of(&self, owner: String) -> Amount {
        self.state
            .balances
            .get(&Account::from_str(&owner).unwrap())
            .await
            .unwrap()
            .unwrap_or(Amount::ZERO)
    }

    // async fn allowance_of(&self, owner: Account, spender: Account) -> Amount {
    async fn allowance_of(&self, owner: String, spender: String) -> Amount {
        match self
            .state
            .allowances
            .get(&Account::from_str(&owner).unwrap())
            .await
            .unwrap()
        {
            Some(allowances) => match allowances.get(&Account::from_str(&spender).unwrap()) {
                Some(&amount) => amount,
                _ => Amount::ZERO,
            },
            _ => Amount::ZERO,
        }
    }

    async fn initial_owner_balance(&self) -> Amount {
        *self.state.initial_owner_balance.get()
    }

    async fn creator_chain_id(&self) -> ChainId {
        self.runtime.application_creator_chain_id()
    }

    async fn meme(&self) -> Meme {
        self.state.meme.get().as_ref().unwrap().clone()
    }
}

struct MutationRoot {
    runtime: Arc<ServiceRuntime<MemeService>>,
}

#[Object]
impl MutationRoot {
    async fn mint(&self, to: Account, amount: Amount) -> [u8; 0] {
        self.runtime
            .schedule_operation(&MemeOperation::Mint { to, amount });
        []
    }
}

#[cfg(test)]
mod service_tests;
