use crate::{big_amount::BigAmount, safe_math};
use async_graphql::{scalar, InputObject, Request, Response, SimpleObject};
use linera_sdk::{
    graphql::GraphQLMutationRoot,
    linera_base_types::{Account, Amount, ApplicationId, ContractAbi, ServiceAbi, Timestamp},
};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use thiserror::Error;

pub struct PoolAbi;

impl ContractAbi for PoolAbi {
    type Operation = PoolOperation;
    type Response = PoolResponse;
}

impl ServiceAbi for PoolAbi {
    type Query = Request;
    type QueryResponse = Response;
}
#[derive(Debug, Copy, Clone, Deserialize, Serialize, GraphQLMutationRoot)]
pub enum PoolOperation {
    // Only for application creator to create pool with virtual initial liquidity
    CreatePool {
        token_0: ApplicationId,
        // None means add pair to native token
        token_1: Option<ApplicationId>,
        // Actual deposited initial liquidity
        // New listed token must not be 0
        amount_0: Amount,
        amount_1: Amount,
    },
    SetFeeTo {
        account: Account,
    },
    SetFeeToSetter {
        account: Account,
    },
    // TODO: AddLiquidity / RemoveLiquidity / Swap
}

#[derive(Debug, Deserialize, Serialize, Default)]
pub enum PoolResponse {
    #[default]
    Ok,
}

#[derive(Debug, Deserialize, Serialize)]
pub enum PoolMessage {
    // Only for application creator to create pool with virtual initial liquidity
    CreatePool {
        token_0: ApplicationId,
        // None means add pair to native token
        token_1: Option<ApplicationId>,
        amount_0_initial: Amount,
        amount_1_initial: Amount,
        amount_0_virtual: Amount,
        amount_1_virtual: Amount,
        block_timestamp: Timestamp,
    },
    SetFeeTo {
        account: Account,
    },
    SetFeeToSetter {
        account: Account,
    },
}

#[derive(Clone, Copy, Debug, Deserialize, Serialize)]
pub struct PoolParameters {
    pub token_0: ApplicationId,
    pub token_1: Option<ApplicationId>,
    pub router_application_id: ApplicationId,
}

scalar!(PoolParameters);

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize, InputObject)]
pub struct InstantiationArgument {
    pub amount_0: Amount,
    pub amount_1: Amount,
}

// Pool won't touch anything of runtime. Before functions of Pool are called, all action which need
// to be done in runtime must be already done

#[derive(Debug, Error)]
pub enum PoolError {}

#[derive(Debug, Clone, Deserialize, Serialize, Eq, PartialEq, Default, SimpleObject)]
pub struct Share {
    pub total_supply: Amount,
    pub shares: HashMap<Account, Amount>,
}

impl Share {
    pub fn mint(&mut self, to: Account, amount: Amount) {
        self.total_supply.saturating_add_assign(amount);
        self.shares.insert(
            to.clone(),
            self.shares
                .get(&to)
                .unwrap_or(&Amount::ZERO)
                .saturating_add(amount),
        );
    }

    // Liquidity to be burn should be returned to application already
    pub fn burn(&mut self, from: Account, liquidity: Amount) {
        self.total_supply = self.total_supply.saturating_sub(liquidity);
        self.shares.insert(
            from.clone(),
            self.shares
                .get(&from)
                .unwrap_or(&Amount::ZERO)
                .saturating_sub(liquidity),
        );
    }
}

#[derive(Debug, Clone, Deserialize, Eq, PartialEq, Serialize, SimpleObject)]
pub struct Pool {
    pub token_0: ApplicationId,
    // None means add pair to native token
    pub token_1: Option<ApplicationId>,
    pub reserve_0: Amount,
    pub reserve_1: Amount,
    pub pool_fee_percent: u16,
    pub protocol_fee_percent: u16,
    pub share: Share,
    pub fee_to: Account,
    pub fee_to_setter: Account,
    pub price_0_cumulative: BigAmount,
    pub price_1_cumulative: BigAmount,
    pub k_last: Amount,
    pub block_timestamp: Timestamp,
}

impl Pool {
    pub fn create(
        token_0: ApplicationId,
        token_1: Option<ApplicationId>,
        virtual_initial_liquidity: bool,
        amount_0: Amount,
        amount_1: Amount,
        pool_fee_percent: u16,
        protocol_fee_percent: u16,
        creator: Account,
        block_timestamp: Timestamp,
    ) -> Self {
        assert!(amount_0 > Amount::ZERO, "Invalid amount");
        assert!(amount_1 > Amount::ZERO, "Invalid amount");
        assert!(Some(token_0) != token_1, "Invalid token pair");

        let mut pool = Pool {
            token_0,
            token_1,
            reserve_0: Amount::ZERO,
            reserve_1: Amount::ZERO,
            pool_fee_percent,
            protocol_fee_percent,
            share: Share::default(),
            fee_to: creator,
            fee_to_setter: creator,
            price_0_cumulative: BigAmount::default(),
            price_1_cumulative: BigAmount::default(),
            k_last: Amount::ZERO,
            block_timestamp,
        };

        if !virtual_initial_liquidity {
            pool.mint_shares(amount_0, amount_1, creator);
        }
        pool.liquid(amount_0, amount_1, block_timestamp);

        pool
    }

    fn calculate_liquidity(&self, amount_0: Amount, amount_1: Amount) -> Amount {
        let total_supply = self.share.total_supply;

        if total_supply == Amount::ZERO {
            safe_math::mul_then_sqrt(amount_0, amount_1)
        } else {
            safe_math::mul_then_div(amount_0, total_supply, self.reserve_0).min(
                safe_math::mul_then_div(amount_1, total_supply, self.reserve_1),
            )
        }
    }

    fn mint_fee(&mut self) {
        if self.k_last == Amount::ZERO {
            return;
        }
        let root_k = safe_math::mul_then_sqrt(self.reserve_0, self.reserve_1);
        let root_k_last = self.k_last;
        if root_k > root_k_last {
            let denominator = safe_math::mul_then_add(root_k, Amount::from_attos(5), root_k_last);
            let liquidity = safe_math::mul_then_div(
                self.share.total_supply,
                root_k.saturating_sub(root_k_last.into()),
                denominator,
            );
            if liquidity > Amount::ZERO {
                self.share.mint(self.fee_to, liquidity);
            }
        }
    }

    fn liquid(&mut self, amount_0: Amount, amount_1: Amount, block_timestamp: Timestamp) {
        let balance_0 = self.reserve_0.saturating_add(amount_0);
        let balance_1 = self.reserve_1.saturating_add(amount_1);

        let time_elapsed = u128::from(
            block_timestamp
                .delta_since(self.block_timestamp)
                .as_micros(),
        );
        if time_elapsed > 0 && self.reserve_0 > Amount::ZERO && self.reserve_1 > Amount::ZERO {
            (self.price_0_cumulative, self.price_1_cumulative) =
                self.calculate_price_cumulative_pair(time_elapsed);
        }

        self.reserve_0 = balance_0;
        self.reserve_1 = balance_1;
        self.block_timestamp = block_timestamp;
        self.k_last = safe_math::mul_then_sqrt(self.reserve_0, self.reserve_1);
    }

    fn mint_shares(&mut self, amount_0: Amount, amount_1: Amount, to: Account) {
        self.mint_fee();
        let liquidity = self.calculate_liquidity(amount_0, amount_1);
        self.share.mint(to, liquidity);
    }

    pub fn calculate_price_cumulative_pair(&self, time_elapsed: u128) -> (BigAmount, BigAmount) {
        let mut price_0_cumulative = self.price_0_cumulative.clone();
        let mut price_1_cumulative = self.price_1_cumulative.clone();

        if time_elapsed > 0 && self.reserve_0 > Amount::ZERO && self.reserve_1 > Amount::ZERO {
            price_0_cumulative =
                self.price_0_cumulative
                    .clone()
                    .add(safe_math::div_then_mul_to_big_amount(
                        self.reserve_1,
                        self.reserve_0,
                        Amount::from_attos(time_elapsed),
                    ));
            price_1_cumulative =
                self.price_1_cumulative
                    .clone()
                    .add(safe_math::div_then_mul_to_big_amount(
                        self.reserve_0,
                        self.reserve_1,
                        Amount::from_attos(time_elapsed),
                    ));
        }
        (price_0_cumulative, price_1_cumulative)
    }
}

#[cfg(test)]
mod tests {
    use linera_sdk::linera_base_types::{
        Account, AccountOwner, Amount, ApplicationId, ChainId, Owner,
    };
    use std::str::FromStr;

    use super::Pool;

    #[test]
    fn create_pool_with_virtual_initial_liquidity() {
        let token_0 = ApplicationId::from_str("b94e486abcfc016e937dad4297523060095f405530c95d498d981a94141589f167693295a14c3b48460ad6f75d67d2414428227550eb8cee8ecaa37e8646518300aee928d4bf3880353b4a3cd9b6f88e6cc6e5ed050860abae439e7782e9b2dfe8020000000000000000000000").unwrap();
        let token_1 = ApplicationId::from_str("b94e486abcfc016e937dad4297523060095f405530c95d498d981a94141589f167693295a14c3b48460ad6f75d67d2414428227550eb8cee8ecaa37e8646518300aee928d4bf3880353b4a3cd9b6f88e6cc6e5ed050860abae439e7782e9b2dfe8020000000000000000000001").unwrap();
        let owner =
            Owner::from_str("5279b3ae14d3b38e14b65a74aefe44824ea88b25c7841836e9ec77d991a5bc7f")
                .unwrap();
        let chain_id =
            ChainId::from_str("aee928d4bf3880353b4a3cd9b6f88e6cc6e5ed050860abae439e7782e9b2dfe8")
                .unwrap();
        let creator = Account {
            chain_id,
            owner: Some(AccountOwner::User(owner)),
        };

        let pool = Pool::create(
            token_0,
            Some(token_1),
            true,
            Amount::ONE,
            Amount::ONE.try_mul(10).unwrap(),
            30,
            5,
            creator,
            0.into(),
        );

        assert_eq!(pool.token_0, token_0);
        assert_eq!(pool.token_1, Some(token_1));
        assert_eq!(pool.reserve_0, Amount::ONE);
        assert_eq!(pool.reserve_1, Amount::ONE.try_mul(10).unwrap());
    }
}
