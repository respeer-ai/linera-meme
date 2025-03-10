use async_graphql::{scalar, InputObject, Request, Response, SimpleObject};
use linera_sdk::{
    graphql::GraphQLMutationRoot,
    linera_base_types::{Account, Amount, ApplicationId, ContractAbi, ServiceAbi, Timestamp},
};
use primitive_types::U256;
use rust_decimal::prelude::*;
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
    // TODO: AddLiquidity / RemoveLiquidity
    Swap {
        // Used to refund
        amount_0_in: Option<Amount>,
        amount_1_in: Option<Amount>,
        amount_0_out_min: Option<Amount>,
        amount_1_out_min: Option<Amount>,
        to: Option<Account>,
        block_timestamp: Option<Timestamp>,
    },
}

#[derive(Debug, Deserialize, Serialize, Default)]
pub enum PoolResponse {
    #[default]
    Ok,
}

#[derive(Debug, Deserialize, Serialize)]
pub enum PoolMessage {
    // Sent from user chain to meme chain
    RequestFund {
        token: ApplicationId,
        transfer_id: u64,
        amount: Amount,
    },
    // Sent from meme chain to user chain
    FundSuccess {
        transfer_id: u64,
    },
    FundFail {
        transfer_id: u64,
        error: String,
    },
    Swap {
        // Used to refund
        origin: Account,
        amount_0_in: Option<Amount>,
        amount_1_in: Option<Amount>,
        amount_0_out_min: Option<Amount>,
        amount_1_out_min: Option<Amount>,
        to: Option<Account>,
        block_timestamp: Option<Timestamp>,
    },
}

#[derive(Clone, Copy, Debug, Deserialize, Serialize)]
pub struct PoolParameters {
    pub token_0: ApplicationId,
    pub token_1: Option<ApplicationId>,
    pub virtual_initial_liquidity: bool,
}

scalar!(PoolParameters);

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize, InputObject)]
pub struct InstantiationArgument {
    pub amount_0: Amount,
    pub amount_1: Amount,
    pub pool_fee_percent_mul_100: u16,
    pub protocol_fee_percent_mul_100: u16,
    pub router_application_id: ApplicationId,
}

// Pool won't touch anything of runtime. Before functions of Pool are called, all action which need
// to be done in runtime must be already done

#[derive(Debug, Error)]
pub enum PoolError {
    #[error("Invalid amount")]
    InvalidAmount,

    #[error("Borken K")]
    BrokenK,

    #[error("Insufficient liquidity")]
    InsufficientLiquidity,
}

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

#[derive(Debug, Clone, Deserialize, Eq, PartialEq, Serialize)]
pub struct Pool {
    pub token_0: ApplicationId,
    // None means add pair to native token
    pub token_1: Option<ApplicationId>,
    pub reserve_0: Amount,
    pub reserve_1: Amount,
    pub pool_fee_percent_mul_100: u16,
    pub protocol_fee_percent_mul_100: u16,
    pub share: Share,
    pub fee_to: Account,
    pub fee_to_setter: Account,
    pub price_0_cumulative: Decimal,
    pub price_1_cumulative: Decimal,
    pub k_last: Amount,
    pub block_timestamp: Timestamp,
}

scalar!(Pool);

impl Pool {
    pub fn create(
        token_0: ApplicationId,
        token_1: Option<ApplicationId>,
        virtual_initial_liquidity: bool,
        amount_0: Amount,
        amount_1: Amount,
        pool_fee_percent_mul_100: u16,
        protocol_fee_percent_mul_100: u16,
        creator: Account,
        block_timestamp: Timestamp,
    ) -> Self {
        assert!(Some(token_0) != token_1, "Invalid token pair");

        let mut pool = Pool {
            token_0,
            token_1,
            reserve_0: Amount::ZERO,
            reserve_1: Amount::ZERO,
            pool_fee_percent_mul_100,
            protocol_fee_percent_mul_100,
            share: Share::default(),
            fee_to: creator,
            fee_to_setter: creator,
            price_0_cumulative: Decimal::default(),
            price_1_cumulative: Decimal::default(),
            k_last: Amount::ZERO,
            block_timestamp,
        };

        if !virtual_initial_liquidity {
            pool.mint_shares(amount_0, amount_1, creator);
        }

        assert!(amount_0 > Amount::ZERO, "Invalid amount");
        assert!(amount_1 > Amount::ZERO, "Invalid amount");

        pool.liquid(amount_0, amount_1, block_timestamp);

        pool
    }

    fn calculate_liquidity(&self, amount_0: Amount, amount_1: Amount) -> Amount {
        if self.reserve_0 == Amount::ZERO && self.reserve_1 == Amount::ZERO {
            return Amount::from_attos(
                U256::from(u128::from(amount_0))
                    .checked_mul(U256::from(u128::from(amount_1)))
                    .unwrap()
                    .integer_sqrt()
                    .as_u128(),
            );
        }

        let total_supply = self.share.total_supply;
        let reserve_0 = self.reserve_0.saturating_add(amount_0);
        let reserve_1 = self.reserve_1.saturating_add(amount_1);

        if total_supply == Amount::ZERO {
            Amount::from_attos(
                U256::from(u128::from(amount_0))
                    .checked_mul(U256::from(u128::from(amount_1)))
                    .unwrap()
                    .integer_sqrt()
                    .as_u128(),
            )
        } else {
            Amount::from_attos(
                U256::from(u128::from(amount_0))
                    .checked_mul(U256::from(u128::from(total_supply)))
                    .unwrap()
                    .checked_div(U256::from(u128::from(reserve_0)))
                    .unwrap()
                    .min(
                        U256::from(U256::from(u128::from(amount_1)))
                            .checked_mul(U256::from(u128::from(total_supply)))
                            .unwrap()
                            .checked_div(U256::from(u128::from(reserve_1)))
                            .unwrap(),
                    )
                    .as_u128(),
            )
        }
    }

    fn mint_fee(&mut self) {
        if self.k_last == Amount::ZERO {
            return;
        }
        let root_k = U256::from(u128::from(self.reserve_0))
            .checked_mul(U256::from(u128::from(self.reserve_1)))
            .unwrap()
            .integer_sqrt();
        let root_k_last = U256::from(u128::from(self.k_last));
        if root_k > root_k_last {
            let denominator = root_k
                .checked_mul(U256::from(5))
                .unwrap()
                .checked_add(root_k_last)
                .unwrap();
            let liquidity = Amount::from_attos(
                U256::from(u128::from(self.share.total_supply))
                    .checked_mul(root_k.checked_sub(root_k_last).unwrap())
                    .unwrap()
                    .checked_div(denominator)
                    .unwrap()
                    .as_u128(),
            );
            if liquidity > Amount::ZERO {
                self.share.mint(self.fee_to, liquidity);
            }
        }
    }

    // TODO: this should be calculate only once for each block
    pub fn liquid(&mut self, balance_0: Amount, balance_1: Amount, block_timestamp: Timestamp) {
        let time_elapsed = u128::from(
            block_timestamp
                .delta_since(self.block_timestamp)
                .as_duration()
                .as_secs(),
        );
        if time_elapsed > 0 && self.reserve_0 > Amount::ZERO && self.reserve_1 > Amount::ZERO {
            (self.price_0_cumulative, self.price_1_cumulative) =
                self.calculate_price_cumulative_pair(time_elapsed);
        }

        self.reserve_0 = balance_0;
        self.reserve_1 = balance_1;
        self.block_timestamp = block_timestamp;
        self.k_last = Amount::from_attos(
            U256::from(u128::from(self.reserve_0))
                .checked_mul(U256::from(u128::from(self.reserve_1)))
                .unwrap()
                .integer_sqrt()
                .as_u128(),
        );
    }

    pub fn mint_shares(&mut self, amount_0: Amount, amount_1: Amount, to: Account) {
        assert!(amount_0 > Amount::ZERO, "Invalid amount");
        assert!(amount_1 > Amount::ZERO, "Invalid amount");

        self.mint_fee();
        let liquidity = self.calculate_liquidity(amount_0, amount_1);
        self.share.mint(to, liquidity);
    }

    pub fn calculate_price_cumulative_pair(&self, time_elapsed: u128) -> (Decimal, Decimal) {
        let mut price_0_cumulative = self.price_0_cumulative.clone();
        let mut price_1_cumulative = self.price_1_cumulative.clone();

        let reserve_0 = Decimal::from_str(&format!("{}", self.reserve_0)).unwrap();
        let reserve_1 = Decimal::from_str(&format!("{}", self.reserve_1)).unwrap();

        if time_elapsed > 0 && self.reserve_0 > Amount::ZERO && self.reserve_1 > Amount::ZERO {
            let time_elapsed = Decimal::from(time_elapsed);
            price_0_cumulative = self
                .price_0_cumulative
                .clone()
                .checked_add(
                    reserve_1
                        .checked_mul(time_elapsed)
                        .unwrap()
                        .checked_div(reserve_0)
                        .unwrap(),
                )
                .unwrap();
            price_1_cumulative = self
                .price_1_cumulative
                .clone()
                .checked_add(
                    reserve_0
                        .checked_mul(time_elapsed)
                        .unwrap()
                        .checked_div(reserve_1)
                        .unwrap(),
                )
                .unwrap();
        }
        (price_0_cumulative, price_1_cumulative)
    }

    pub fn calculate_swap_amount_1(&self, amount_0: Amount) -> Result<Amount, PoolError> {
        if self.reserve_0 <= Amount::ZERO || self.reserve_1 <= Amount::ZERO {
            return Err(PoolError::InvalidAmount);
        }
        Ok(Amount::from_attos(
            U256::from(u128::from(amount_0))
                .checked_mul(U256::from(u128::from(self.reserve_1)))
                .unwrap()
                .checked_div(U256::from(u128::from(self.reserve_0)))
                .unwrap()
                .as_u128(),
        ))
    }

    pub fn calculate_swap_amount_0(&self, amount_1: Amount) -> Result<Amount, PoolError> {
        if self.reserve_0 <= Amount::ZERO || self.reserve_1 <= Amount::ZERO {
            return Err(PoolError::InvalidAmount);
        }
        Ok(Amount::from_attos(
            U256::from(u128::from(amount_1))
                .checked_mul(U256::from(u128::from(self.reserve_0)))
                .unwrap()
                .checked_div(U256::from(u128::from(self.reserve_1)))
                .unwrap()
                .as_u128(),
        ))
    }

    pub fn calculate_adjusted_amount_pair(
        &self,
        amount_0_out: Amount,
        amount_1_out: Amount,
    ) -> Result<(Amount, Amount), PoolError> {
        let amount_0_in = if self.reserve_0 > amount_0_out {
            amount_0_out
        } else {
            Amount::ZERO
        };
        let amount_1_in = if self.reserve_1 > amount_1_out {
            amount_1_out
        } else {
            Amount::ZERO
        };
        if amount_0_in <= Amount::ZERO && amount_1_in <= Amount::ZERO {
            return Err(PoolError::InsufficientLiquidity);
        }
        let balance_0_adjusted = U256::from(u128::from(self.reserve_0))
            .checked_sub(
                // Fee percent already scale to 100 larger
                U256::from(u128::from(amount_0_in))
                    .checked_mul(U256::from(self.pool_fee_percent_mul_100))
                    .unwrap()
                    .checked_div(U256::from(10000))
                    .unwrap(),
            )
            .unwrap();
        let balance_1_adjusted = U256::from(u128::from(self.reserve_1))
            .checked_sub(
                // Fee percent already scale to 100 larger
                U256::from(u128::from(amount_1_in))
                    .checked_mul(U256::from(self.pool_fee_percent_mul_100))
                    .unwrap()
                    .checked_div(U256::from(10000))
                    .unwrap(),
            )
            .unwrap();
        if balance_0_adjusted.checked_mul(balance_1_adjusted)
            >= U256::from(u128::from(self.reserve_0))
                .checked_mul(U256::from(u128::from(self.reserve_1)))
        {
            return Err(PoolError::BrokenK);
        }

        Ok((amount_0_in, amount_1_in))
    }
}

#[cfg(test)]
mod tests {
    use linera_sdk::linera_base_types::{
        Account, AccountOwner, Amount, ApplicationId, ChainId, Owner,
    };
    use rust_decimal::prelude::*;
    use std::str::FromStr;

    use super::Pool;

    #[test]
    fn test_pool_with_virtual_initial_liquidity() {
        let _ = env_logger::builder().is_test(true).try_init();

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
            Amount::from_str("21.2342").unwrap(),
            30,
            5,
            creator,
            0.into(),
        );

        assert_eq!(pool.token_0, token_0);
        assert_eq!(pool.token_1, Some(token_1));
        assert_eq!(pool.share.total_supply, Amount::ZERO);
        assert_eq!(pool.reserve_0, Amount::ONE);
        assert_eq!(pool.reserve_1, Amount::from_str("21.2342").unwrap());

        let (price_0_cumulative, price_1_cumulative) = pool.calculate_price_cumulative_pair(1);
        assert_eq!(
            price_1_cumulative,
            Decimal::from_str("0.0470938391839579546203765623").unwrap()
        );
        assert_eq!(price_0_cumulative, Decimal::from_str("21.2342").unwrap());

        let (price_0_cumulative, price_1_cumulative) = pool.calculate_price_cumulative_pair(2);
        assert_eq!(
            price_1_cumulative,
            Decimal::from_str("0.0941876783679159092407531247").unwrap()
        );
        assert_eq!(price_0_cumulative, Decimal::from_str("42.4684").unwrap());
    }

    #[test]
    fn test_pool_with_real_initial_liquidity() {
        let _ = env_logger::builder().is_test(true).try_init();

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
            false,
            Amount::ONE,
            Amount::from_str("21.2342").unwrap(),
            30,
            5,
            creator,
            0.into(),
        );

        assert_eq!(pool.token_0, token_0);
        assert_eq!(pool.token_1, Some(token_1));
        assert_eq!(pool.reserve_0, Amount::ONE);
        assert_eq!(pool.reserve_1, Amount::from_str("21.2342").unwrap());

        // Test initial liquidity
        let liquidity = Amount::from_attos(4608058159355196332);
        assert_eq!(pool.share.total_supply, liquidity);
        assert_eq!(pool.share.shares.contains_key(&creator), true);
        assert_eq!(*pool.share.shares.get(&creator).unwrap(), liquidity);
    }
}
