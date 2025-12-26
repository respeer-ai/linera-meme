// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

#![cfg_attr(target_arch = "wasm32", no_main)]

use std::{str::FromStr, sync::Arc};

use abi::swap::{
    pool::{Pool, PoolAbi, PoolOperation, PoolParameters},
    transaction::Transaction,
};
use async_graphql::{EmptySubscription, Object, Request, Response, Schema};
use linera_sdk::{
    linera_base_types::{Account, Amount, Timestamp, WithServiceAbi},
    views::View,
    Service, ServiceRuntime,
};

use pool::{interfaces::state::StateInterface, state::PoolState, FundRequest, LiquidityAmount};

#[derive(Clone)]
pub struct PoolService {
    state: Arc<PoolState>,
    runtime: Arc<ServiceRuntime<Self>>,
}

linera_sdk::service!(PoolService);

impl WithServiceAbi for PoolService {
    type Abi = PoolAbi;
}

impl Service for PoolService {
    type Parameters = PoolParameters;

    async fn new(runtime: ServiceRuntime<Self>) -> Self {
        let _ = runtime.application_parameters();

        let state = PoolState::load(runtime.root_view_storage_context())
            .await
            .expect("Failed to load state");
        PoolService {
            state: Arc::new(state),
            runtime: Arc::new(runtime),
        }
    }

    async fn handle_query(&self, request: Request) -> Response {
        let schema = Schema::build(
            QueryRoot {
                service: self.clone(),
            },
            MutationRoot {
                service: self.clone(),
            },
            EmptySubscription,
        )
        .finish();
        schema.execute(request).await
    }
}

impl PoolService {
    fn virtual_initial_liquidity(&self) -> bool {
        self.runtime
            .application_parameters()
            .virtual_initial_liquidity
    }

    fn state(&self) -> Arc<PoolState> {
        self.state.clone()
    }
}

struct QueryRoot {
    service: PoolService,
}

#[Object]
impl QueryRoot {
    async fn pool(&self) -> Pool {
        self.service.state.pool.get().as_ref().unwrap().clone()
    }

    async fn fund_requests(&self) -> Vec<FundRequest> {
        self.service
            .state
            .fund_requests
            .index_values()
            .await
            .unwrap()
            .into_iter()
            .map(|(_, v)| v)
            .collect()
    }

    // async fn liquidity(&self, owner: Account) -> Amount {
    async fn liquidity(&self, owner: String) -> LiquidityAmount {
        // TODO: we have to access state directly instead of liquidity() right now due to `Send`
        let liquidity = self
            .service
            .state
            .as_ref()
            .shares
            .get(&Account::from_str(&owner).unwrap())
            .await
            .expect("Failed: liquidity")
            .unwrap_or(Amount::ZERO);
        let (amount_0, amount_1) = self
            .service
            .state
            .try_calculate_liquidity_amount_pair(liquidity, None, None)
            .unwrap_or((Amount::ZERO, Amount::ZERO));
        LiquidityAmount {
            liquidity,
            amount_0,
            amount_1,
        }
    }

    async fn virtual_initial_liquidity(&self) -> bool {
        self.service.virtual_initial_liquidity()
    }

    async fn latest_transactions(&self, start_id: Option<u32>) -> Vec<Transaction> {
        let mut transactions: Vec<_> = self
            .service
            .state()
            .latest_transactions
            .elements()
            .await
            .expect("Failed get transactions")
            .into_iter()
            .filter(|transaction| transaction.transaction_id >= start_id)
            .collect();
        transactions.sort_by(|a, b| a.created_at.cmp(&b.created_at));
        transactions
    }

    async fn calculate_amount_liquidity(
        &self,
        amount_0_desired: Option<Amount>,
        amount_1_desired: Option<Amount>,
    ) -> LiquidityAmount {
        assert!(
            amount_0_desired.is_some() || amount_1_desired.is_some(),
            "Invalid amount"
        );
        let amount_0 = amount_0_desired.unwrap_or(Amount::MAX);
        let amount_1 = amount_1_desired.unwrap_or(Amount::MAX);
        let (amount_0, amount_1) = self
            .service
            .state
            .pool
            .get()
            .as_ref()
            .unwrap()
            .try_calculate_swap_amount_pair(amount_0, amount_1, None, None)
            .expect("Failed calculate amount pair");
        let total_supply = self.service.state.total_supply.get();
        let liquidity = self
            .service
            .state
            .pool
            .get()
            .as_ref()
            .unwrap()
            .calculate_liquidity(*total_supply, amount_0, amount_1);
        LiquidityAmount {
            liquidity,
            amount_0,
            amount_1,
        }
    }
}

struct MutationRoot {
    service: PoolService,
}

#[Object]
impl MutationRoot {
    async fn swap(
        &self,
        amount_0_in: Option<Amount>,
        amount_1_in: Option<Amount>,
        amount_0_out_min: Option<Amount>,
        amount_1_out_min: Option<Amount>,
        to: Option<Account>,
        block_timestamp: Option<Timestamp>,
    ) -> [u8; 0] {
        // Mutation should always be from other chain
        assert!(
            self.service.runtime.application_creator_chain_id() != self.service.runtime.chain_id(),
            "Permission denied"
        );

        self.service
            .runtime
            .schedule_operation(&PoolOperation::Swap {
                amount_0_in,
                amount_1_in,
                amount_0_out_min,
                amount_1_out_min,
                to,
                block_timestamp,
            });
        []
    }
}

#[cfg(test)]
mod tests {
    #[test]
    fn query() {}
}
