// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

#![cfg_attr(target_arch = "wasm32", no_main)]

use std::sync::Arc;

use abi::{
    meme_token::MemeToken,
    swap::pool::{BootstrapPolicy, Pool, PoolAbi, PoolOperation, PoolParameters},
};
use async_graphql::{EmptySubscription, Object, Request, Response, Schema};
use linera_sdk::{
    linera_base_types::{Account, Amount, ApplicationId, Timestamp, WithServiceAbi},
    views::View,
    Service, ServiceRuntime,
};

use pool::{state::PoolState, FundRequest, LiquidityAmount};

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
        match self.runtime.application_parameters().bootstrap_policy {
            BootstrapPolicy::UserCreatePool => false,
            BootstrapPolicy::MemeInitializeLiquidity {
                virtual_initial_liquidity,
            } => virtual_initial_liquidity,
        }
    }
}

fn effective_total_supply(pool: &Pool, total_supply: Amount) -> Amount {
    total_supply.try_add(pool.mint_fee(total_supply)).unwrap()
}

fn query_liquidity_amounts(
    pool: &Pool,
    liquidity: Amount,
    total_supply: Amount,
) -> (Amount, Amount) {
    let effective_supply = effective_total_supply(pool, total_supply);
    pool.try_calculate_liquidity_amount_pair(liquidity, effective_supply, None, None)
        .unwrap_or((Amount::ZERO, Amount::ZERO))
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

    async fn liquidity(&self, owner: Account) -> LiquidityAmount {
        // TODO: we have to access state directly instead of liquidity() right now due to `Send`
        let pool = self.service.state.pool.get().as_ref().unwrap().clone();
        let total_supply = *self.service.state.total_supply.get();
        let liquidity = self
            .service
            .state
            .as_ref()
            .shares
            .get(&owner)
            .await
            .expect("Failed: liquidity")
            .unwrap_or(Amount::ZERO);
        let (amount_0, amount_1) = query_liquidity_amounts(&pool, liquidity, total_supply);
        LiquidityAmount {
            liquidity,
            amount_0,
            amount_1,
        }
    }

    async fn claimable_balance(&self, token: Option<ApplicationId>, owner: Account) -> Amount {
        self.service
            .state
            .claimable_balances
            .get(&MemeToken::from(token))
            .await
            .expect("Failed to read claimable balance")
            .and_then(|balances| balances.get(&owner).copied())
            .unwrap_or(Amount::ZERO)
    }

    async fn claiming_balance(&self, token: Option<ApplicationId>, owner: Account) -> Amount {
        self.service
            .state
            .claiming_balances
            .get(&MemeToken::from(token))
            .await
            .expect("Failed to read claiming balance")
            .and_then(|balances| balances.get(&owner).copied())
            .unwrap_or(Amount::ZERO)
    }

    async fn total_supply(&self) -> Amount {
        let pool = self.service.state.pool.get().as_ref().unwrap().clone();
        effective_total_supply(&pool, *self.service.state.total_supply.get())
    }

    async fn virtual_initial_liquidity(&self) -> bool {
        self.service.virtual_initial_liquidity()
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
        let pool = self.service.state.pool.get().as_ref().unwrap().clone();
        let liquidity = self
            .service
            .state
            .pool
            .get()
            .as_ref()
            .unwrap()
            .calculate_liquidity(
                effective_total_supply(&pool, *total_supply),
                amount_0,
                amount_1,
            );
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

    async fn claim(&self, token: Option<ApplicationId>, amount: Amount) -> [u8; 0] {
        assert!(
            self.service.runtime.application_creator_chain_id() != self.service.runtime.chain_id(),
            "Permission denied"
        );

        self.service
            .runtime
            .schedule_operation(&PoolOperation::Claim { token, amount });
        []
    }

    async fn add_liquidity(
        &self,
        amount_0_in: Amount,
        amount_1_in: Amount,
        amount_0_out_min: Option<Amount>,
        amount_1_out_min: Option<Amount>,
        to: Option<Account>,
        block_timestamp: Option<Timestamp>,
    ) -> [u8; 0] {
        assert!(
            self.service.runtime.application_creator_chain_id() != self.service.runtime.chain_id(),
            "Permission denied"
        );

        self.service
            .runtime
            .schedule_operation(&PoolOperation::AddLiquidity {
                amount_0_in,
                amount_1_in,
                amount_0_out_min,
                amount_1_out_min,
                to,
                block_timestamp,
            });
        []
    }

    async fn remove_liquidity(
        &self,
        liquidity: Amount,
        amount_0_out_min: Option<Amount>,
        amount_1_out_min: Option<Amount>,
        to: Option<Account>,
        block_timestamp: Option<Timestamp>,
    ) -> [u8; 0] {
        assert!(
            self.service.runtime.application_creator_chain_id() != self.service.runtime.chain_id(),
            "Permission denied"
        );

        self.service
            .runtime
            .schedule_operation(&PoolOperation::RemoveLiquidity {
                liquidity,
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
    use super::{effective_total_supply, query_liquidity_amounts, PoolService};
    use abi::{meme_token::MemeToken, swap::pool::Pool};
    use async_graphql::{Request, Variables};
    use linera_sdk::{
        linera_base_types::{Account, AccountOwner, Amount, ApplicationId, ChainId},
        views::View,
        Service, ServiceRuntime,
    };
    use pool::state::PoolState;
    use serde_json::{json, Value};
    use std::{
        collections::{BTreeSet, HashMap},
        str::FromStr,
        sync::Arc,
    };

    fn sample_pool_after_swap_growth() -> (Pool, Amount) {
        let token_0 = ApplicationId::from_str(
            "b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bad",
        )
        .unwrap();
        let token_1 = ApplicationId::from_str(
            "b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bae",
        )
        .unwrap();
        let owner = AccountOwner::from_str(
            "0x5279b3ae14d3b38e14b65a74aefe44824ea88b25c7841836e9ec77d991a5bc7f",
        )
        .unwrap();
        let chain_id =
            ChainId::from_str("aee928d4bf3880353b4a3cd9b6f88e6cc6e5ed050860abae439e7782e9b2dfe8")
                .unwrap();
        let creator = Account { chain_id, owner };

        let mut pool = Pool::create(token_0, Some(token_1), 30, creator, 0.into());
        pool.reserve_0 = Amount::from_str("90.933891061198508684").unwrap();
        pool.reserve_1 = Amount::from_str("110").unwrap();
        pool.k_last = Amount::from_str("100").unwrap();
        (pool, Amount::from_str("100").unwrap())
    }

    #[test]
    fn query() {}

    #[tokio::test]
    async fn mutation_schema_exposes_frontend_liquidity_entrypoints() {
        let runtime = Arc::new(ServiceRuntime::<PoolService>::new());
        let state = PoolState::load(runtime.root_view_storage_context())
            .await
            .expect("Failed to read from mock key value store");
        let service = PoolService {
            state: Arc::new(state),
            runtime,
        };

        let response = service
            .handle_query(Request::new(
                r#"
                query MutationFields {
                    __schema {
                        mutationType {
                            fields {
                                name
                            }
                        }
                    }
                }
                "#,
            ))
            .await;
        assert!(response.errors.is_empty(), "{:?}", response.errors);

        let data = response.data.into_json().unwrap();
        let names = data["__schema"]["mutationType"]["fields"]
            .as_array()
            .unwrap()
            .iter()
            .map(|field| field["name"].as_str().unwrap())
            .collect::<BTreeSet<_>>();

        assert!(names.contains("swap"));
        assert!(names.contains("claim"));
        assert!(names.contains("addLiquidity"));
        assert!(names.contains("removeLiquidity"));
    }

    #[tokio::test]
    async fn claim_balance_queries_return_single_pool_aggregate_state() {
        let runtime = Arc::new(ServiceRuntime::<PoolService>::new());
        let mut state = PoolState::load(runtime.root_view_storage_context())
            .await
            .expect("Failed to read from mock key value store");

        let owner = Account {
            chain_id: ChainId::from_str(
                "aee928d4bf3880353b4a3cd9b6f88e6cc6e5ed050860abae439e7782e9b2dfe8",
            )
            .unwrap(),
            owner: AccountOwner::from_str(
                "0x5279b3ae14d3b38e14b65a74aefe44824ea88b25c7841836e9ec77d991a5bc7f",
            )
            .unwrap(),
        };
        let other_owner = Account {
            chain_id: ChainId::from_str(
                "899dd894c41297e9dd1221fa02845efc81ed8abd9a0b7d203ad514b3aa6b2d46",
            )
            .unwrap(),
            owner: AccountOwner::from_str(
                "0x02e900512d2fca22897f80a2f6932ff454f2752ef7afad18729dd25e5b5b6e00",
            )
            .unwrap(),
        };
        let token = ApplicationId::from_str(
            "b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bad",
        )
        .unwrap();
        let other_token = ApplicationId::from_str(
            "b10ac11c3569d9e1b6e22fe50f8c1de8b33a01173b4563c614aa07d8b8eb5bae",
        )
        .unwrap();

        state
            .claimable_balances
            .insert(
                &MemeToken::Native,
                HashMap::from([(owner, Amount::from_tokens(7))]),
            )
            .unwrap();
        state
            .claimable_balances
            .insert(
                &MemeToken::Fungible(other_token),
                HashMap::from([(owner, Amount::from_tokens(13))]),
            )
            .unwrap();
        state
            .claiming_balances
            .insert(
                &MemeToken::Fungible(token),
                HashMap::from([(owner, Amount::from_tokens(3))]),
            )
            .unwrap();
        state
            .claiming_balances
            .insert(
                &MemeToken::Native,
                HashMap::from([(other_owner, Amount::from_tokens(11))]),
            )
            .unwrap();

        let service = PoolService {
            state: Arc::new(state),
            runtime,
        };

        let native_balances = query_claim_balances(&service, None, owner).await;
        assert_eq!(
            native_balances["claimableBalance"],
            json!(Amount::from_tokens(7))
        );
        assert_eq!(native_balances["claimingBalance"], json!(Amount::ZERO));

        let fungible_balances = query_claim_balances(&service, Some(token), owner).await;
        assert_eq!(fungible_balances["claimableBalance"], json!(Amount::ZERO));
        assert_eq!(
            fungible_balances["claimingBalance"],
            json!(Amount::from_tokens(3))
        );

        let missing_owner_balances = query_claim_balances(&service, Some(token), other_owner).await;
        assert_eq!(
            missing_owner_balances["claimableBalance"],
            json!(Amount::ZERO)
        );
        assert_eq!(
            missing_owner_balances["claimingBalance"],
            json!(Amount::ZERO)
        );
    }

    #[test]
    fn total_supply_query_includes_pending_protocol_fee_dilution() {
        let (pool, total_supply) = sample_pool_after_swap_growth();

        assert_eq!(
            effective_total_supply(&pool, total_supply),
            Amount::from_str("100.002272933913650825").unwrap(),
        );
    }

    #[test]
    fn liquidity_query_uses_effective_total_supply_after_swap_growth() {
        let (pool, total_supply) = sample_pool_after_swap_growth();
        let (amount_0, amount_1) =
            query_liquidity_amounts(&pool, Amount::from_str("100").unwrap(), total_supply);

        assert_eq!(amount_0, Amount::from_str("90.931824240927035291").unwrap());
        assert_eq!(
            amount_1,
            Amount::from_str("109.997499829522206781").unwrap()
        );
    }

    async fn query_claim_balances(
        service: &PoolService,
        token: Option<ApplicationId>,
        owner: Account,
    ) -> Value {
        let request = Request::new(
            r#"
            query ClaimBalances($token: ApplicationId, $owner: Account!) {
                claimableBalance(token: $token, owner: $owner)
                claimingBalance(token: $token, owner: $owner)
            }
            "#,
        )
        .variables(Variables::from_json(json!({
            "token": token.map(|token| token.to_string()),
            "owner": {
                "chain_id": owner.chain_id.to_string(),
                "owner": owner.owner.to_string(),
            }
        })));

        let response = service.handle_query(request).await;
        assert!(response.errors.is_empty(), "{:?}", response.errors);
        response.data.into_json().unwrap()
    }
}
