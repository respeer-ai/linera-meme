use async_graphql::{scalar, InputObject, Request, Response};
use linera_sdk::{
    graphql::GraphQLMutationRoot,
    linera_base_types::{
        Account, Amount, ApplicationId, ChainId, ContractAbi, ServiceAbi, Timestamp,
    },
};
use primitive_types::U256;
use rust_decimal::prelude::*;
use serde::{Deserialize, Serialize};
use thiserror::Error;

use crate::swap::transaction::Transaction;

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
    SetFeeTo {
        account: Account,
    },
    SetFeeToSetter {
        account: Account,
    },
    AddLiquidity {
        amount_0_in: Amount,
        amount_1_in: Amount,
        amount_0_out_min: Option<Amount>,
        amount_1_out_min: Option<Amount>,
        to: Option<Account>,
        block_timestamp: Option<Timestamp>,
    },
    RemoveLiquidity {
        liquidity: Amount,
        amount_0_out_min: Option<Amount>,
        amount_1_out_min: Option<Amount>,
        to: Option<Account>,
        block_timestamp: Option<Timestamp>,
    },
    Swap {
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

#[derive(Clone, Debug, Deserialize, Serialize)]
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
    AddLiquidity {
        // Used to refund
        origin: Account,
        amount_0_in: Amount,
        amount_1_in: Amount,
        amount_0_out_min: Option<Amount>,
        amount_1_out_min: Option<Amount>,
        to: Option<Account>,
        block_timestamp: Option<Timestamp>,
    },
    RemoveLiquidity {
        // Used to refund
        origin: Account,
        liquidity: Amount,
        amount_0_out_min: Option<Amount>,
        amount_1_out_min: Option<Amount>,
        to: Option<Account>,
        block_timestamp: Option<Timestamp>,
    },
    SetFeeTo {
        operator: Account,
        account: Account,
    },
    SetFeeToSetter {
        operator: Account,
        account: Account,
    },
    NewTransaction {
        transaction: Transaction,
    },
}

#[derive(Clone, Copy, Debug, Deserialize, Serialize)]
pub struct PoolParameters {
    pub creator: Account,
    pub token_0: ApplicationId,
    pub token_1: Option<ApplicationId>,
    pub virtual_initial_liquidity: bool,
    // TODO: work around of https://github.com/linera-io/linera-protocol/issues/3538
    pub token_0_creator_chain_id: ChainId,
    pub token_1_creator_chain_id: Option<ChainId>,
}

scalar!(PoolParameters);

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize, InputObject)]
pub struct InstantiationArgument {
    pub amount_0: Amount,
    pub amount_1: Amount,
    pub pool_fee_percent_mul_100: u16,
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

#[derive(Debug, Clone, Deserialize, Eq, PartialEq, Serialize)]
pub struct Pool {
    pub token_0: ApplicationId,
    // None means add pair to native token
    pub token_1: Option<ApplicationId>,
    pub reserve_0: Amount,
    pub reserve_1: Amount,
    pub pool_fee_percent_mul_100: u16,
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
        pool_fee_percent_mul_100: u16,
        creator: Account,
        block_timestamp: Timestamp,
    ) -> Self {
        assert!(Some(token_0) != token_1, "Invalid token pair");

        Pool {
            token_0,
            token_1,
            reserve_0: Amount::ZERO,
            reserve_1: Amount::ZERO,
            pool_fee_percent_mul_100,
            fee_to: creator,
            fee_to_setter: creator,
            price_0_cumulative: Decimal::default(),
            price_1_cumulative: Decimal::default(),
            k_last: Amount::ZERO,
            block_timestamp,
        }
    }

    pub fn calculate_liquidity(
        &self,
        total_supply: Amount,
        amount_0: Amount,
        amount_1: Amount,
    ) -> Amount {
        if self.reserve_0 == Amount::ZERO && self.reserve_1 == Amount::ZERO {
            return Amount::from_attos(
                U256::from(u128::from(amount_0))
                    .checked_mul(U256::from(u128::from(amount_1)))
                    .unwrap()
                    .integer_sqrt()
                    .as_u128(),
            );
        }

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
                    .checked_div(U256::from(u128::from(self.reserve_0)))
                    .unwrap()
                    .min(
                        U256::from(U256::from(u128::from(amount_1)))
                            .checked_mul(U256::from(u128::from(total_supply)))
                            .unwrap()
                            .checked_div(U256::from(u128::from(self.reserve_1)))
                            .unwrap(),
                    )
                    .as_u128(),
            )
        }
    }

    pub fn mint_fee(&self, total_supply: Amount) -> Amount {
        if self.k_last == Amount::ZERO {
            return Amount::ZERO;
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
                U256::from(u128::from(total_supply))
                    .checked_mul(root_k.checked_sub(root_k_last).unwrap())
                    .unwrap()
                    .checked_div(denominator)
                    .unwrap()
                    .as_u128(),
            );
            if liquidity > Amount::ZERO {
                return liquidity;
            }
        }
        return Amount::ZERO;
    }

    pub fn update_k_last(&mut self) {
        self.k_last = Amount::from_attos(
            U256::from(u128::from(self.reserve_0))
                .checked_mul(U256::from(u128::from(self.reserve_1)))
                .unwrap()
                .integer_sqrt()
                .as_u128(),
        );
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
        if self.reserve_0 <= Amount::ZERO
            || self.reserve_1 <= Amount::ZERO
            || amount_0 <= Amount::ZERO
        {
            return Err(PoolError::InvalidAmount);
        }

        let fee_base = U256::from(10000u128);
        let fee_multiplier = fee_base
            .checked_sub(U256::from(self.pool_fee_percent_mul_100))
            .unwrap();
        let amount_in_with_fee = U256::from(u128::from(amount_0))
            .checked_mul(fee_multiplier)
            .unwrap();
        let numerator = amount_in_with_fee
            .checked_mul(U256::from(u128::from(self.reserve_1)))
            .unwrap();
        let denominator = U256::from(u128::from(self.reserve_0))
            .checked_mul(fee_base)
            .unwrap()
            .checked_add(amount_in_with_fee)
            .unwrap();

        Ok(Amount::from_attos(
            numerator
                .checked_div(denominator)
                .unwrap_or(U256::from(0))
                .as_u128(),
        ))
    }

    pub fn calculate_swap_amount_0(&self, amount_1: Amount) -> Result<Amount, PoolError> {
        if self.reserve_0 <= Amount::ZERO
            || self.reserve_1 <= Amount::ZERO
            || amount_1 <= Amount::ZERO
        {
            return Err(PoolError::InvalidAmount);
        }

        let fee_base = U256::from(10000u128);
        let fee_multiplier = fee_base
            .checked_sub(U256::from(self.pool_fee_percent_mul_100))
            .unwrap();
        let amount_in_with_fee = U256::from(u128::from(amount_1))
            .checked_mul(fee_multiplier)
            .unwrap();
        let numerator = amount_in_with_fee
            .checked_mul(U256::from(u128::from(self.reserve_0)))
            .unwrap();
        let denominator = U256::from(u128::from(self.reserve_1))
            .checked_mul(fee_base)
            .unwrap()
            .checked_add(amount_in_with_fee)
            .unwrap();

        Ok(Amount::from_attos(
            numerator
                .checked_div(denominator)
                .unwrap_or(U256::from(0))
                .as_u128(),
        ))
    }

    pub fn validate_swap_invariant(
        &self,
        amount_0_in: Amount,
        amount_1_in: Amount,
        amount_0_out: Amount,
        amount_1_out: Amount,
    ) -> Result<(), PoolError> {
        if amount_0_in <= Amount::ZERO && amount_1_in <= Amount::ZERO {
            return Err(PoolError::InsufficientLiquidity);
        }
        if amount_0_out >= self.reserve_0 || amount_1_out >= self.reserve_1 {
            return Err(PoolError::InsufficientLiquidity);
        }

        let fee_base = U256::from(10000u128);
        let reserve_0 = U256::from(u128::from(self.reserve_0));
        let reserve_1 = U256::from(u128::from(self.reserve_1));
        let balance_0 = reserve_0
            .checked_add(U256::from(u128::from(amount_0_in)))
            .unwrap()
            .checked_sub(U256::from(u128::from(amount_0_out)))
            .unwrap();
        let balance_1 = reserve_1
            .checked_add(U256::from(u128::from(amount_1_in)))
            .unwrap()
            .checked_sub(U256::from(u128::from(amount_1_out)))
            .unwrap();

        let balance_0_adjusted = balance_0
            .checked_mul(fee_base)
            .unwrap()
            .checked_sub(
                U256::from(u128::from(amount_0_in))
                    .checked_mul(U256::from(self.pool_fee_percent_mul_100))
                    .unwrap(),
            )
            .unwrap();
        let balance_1_adjusted = balance_1
            .checked_mul(fee_base)
            .unwrap()
            .checked_sub(
                U256::from(u128::from(amount_1_in))
                    .checked_mul(U256::from(self.pool_fee_percent_mul_100))
                    .unwrap(),
            )
            .unwrap();

        if balance_0_adjusted.checked_mul(balance_1_adjusted).unwrap()
            < reserve_0
                .checked_mul(reserve_1)
                .unwrap()
                .checked_mul(fee_base)
                .unwrap()
                .checked_mul(fee_base)
                .unwrap()
        {
            return Err(PoolError::BrokenK);
        }

        Ok(())
    }

    pub fn try_calculate_swap_amount_pair(
        &self,
        amount_0_desired: Amount,
        amount_1_desired: Amount,
        amount_0_min: Option<Amount>,
        amount_1_min: Option<Amount>,
    ) -> Result<(Amount, Amount), PoolError> {
        if self.reserve_0 == Amount::ZERO && self.reserve_1 == Amount::ZERO {
            return Ok((amount_0_desired, amount_1_desired));
        }
        let reserve_0 = Decimal::from_str(&format!("{}", self.reserve_0)).unwrap();
        let reserve_1 = Decimal::from_str(&format!("{}", self.reserve_1)).unwrap();
        let amount_0_desired_decimal = Decimal::from_str(&format!("{}", amount_0_desired)).unwrap();
        let amount_1_desired_decimal = Decimal::from_str(&format!("{}", amount_1_desired)).unwrap();

        let amount_1_optimal = Amount::from_str(
            &amount_0_desired_decimal
                .checked_mul(reserve_1)
                .unwrap()
                .checked_div(reserve_0)
                .unwrap()
                .round_dp(Amount::DECIMAL_PLACES as u32)
                .to_string(),
        )
        .unwrap();
        if amount_1_optimal <= amount_1_desired {
            if let Some(amount_1_min) = amount_1_min {
                if amount_1_optimal < amount_1_min {
                    return Err(PoolError::InvalidAmount);
                }
            }
            return Ok((amount_0_desired, amount_1_optimal));
        }
        let amount_0_optimal = Amount::from_str(
            &amount_1_desired_decimal
                .checked_mul(reserve_0)
                .unwrap()
                .checked_div(reserve_1)
                .unwrap()
                .round_dp(Amount::DECIMAL_PLACES as u32)
                .to_string(),
        )
        .unwrap();
        if amount_0_optimal > amount_0_desired {
            return Err(PoolError::InvalidAmount);
        }
        if let Some(amount_0_min) = amount_0_min {
            if amount_0_optimal < amount_0_min {
                return Err(PoolError::InvalidAmount);
            }
        }
        Ok((amount_0_optimal, amount_1_desired))
    }

    pub fn try_calculate_liquidity_amount_pair(
        &self,
        liquidity: Amount,
        total_supply: Amount,
        amount_0_min: Option<Amount>,
        amount_1_min: Option<Amount>,
    ) -> Result<(Amount, Amount), PoolError> {
        let amount_0 = Amount::from_attos(
            U256::from(u128::from(liquidity))
                .checked_mul(U256::from(u128::from(self.reserve_0)))
                .unwrap()
                .checked_div(U256::from(u128::from(total_supply)))
                .unwrap_or(U256::from(0))
                .as_u128(),
        );
        let amount_1 = Amount::from_attos(
            U256::from(u128::from(liquidity))
                .checked_mul(U256::from(u128::from(self.reserve_1)))
                .unwrap()
                .checked_div(U256::from(u128::from(total_supply)))
                .unwrap_or(U256::from(0))
                .as_u128(),
        );

        if amount_0 == Amount::ZERO || amount_1 == Amount::ZERO {
            return Err(PoolError::InvalidAmount);
        }
        if let Some(amount_0_min) = amount_0_min {
            if amount_0 < amount_0_min {
                return Err(PoolError::InvalidAmount);
            }
        }
        if let Some(amount_1_min) = amount_1_min {
            if amount_1 < amount_1_min {
                return Err(PoolError::InvalidAmount);
            }
        }

        Ok((amount_0, amount_1))
    }

    pub fn calculate_price_pair(&self) -> (Amount, Amount) {
        let time_elapsed = 1000;
        let (price_0_cumulative, price_1_cumulative) =
            self.calculate_price_cumulative_pair(time_elapsed as u128);
        (
            Amount::from_str(
                &price_0_cumulative
                    .checked_sub(self.price_0_cumulative)
                    .unwrap()
                    .checked_div(Decimal::new(time_elapsed, 0))
                    .unwrap()
                    .round_dp(Amount::DECIMAL_PLACES as u32)
                    .to_string(),
            )
            .unwrap(),
            Amount::from_str(
                &price_1_cumulative
                    .checked_sub(self.price_1_cumulative)
                    .unwrap()
                    .checked_div(Decimal::new(time_elapsed, 0))
                    .unwrap()
                    .round_dp(Amount::DECIMAL_PLACES as u32)
                    .to_string(),
            )
            .unwrap(),
        )
    }
}

#[cfg(test)]
mod tests {
    use linera_sdk::linera_base_types::{Account, AccountOwner, Amount, ApplicationId, ChainId};
    use rust_decimal::prelude::*;
    use std::str::FromStr;

    use super::Pool;

    #[test]
    fn test_pool_with_virtual_initial_liquidity() {
        let _ = env_logger::builder().is_test(true).try_init();

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

        assert_eq!(pool.token_0, token_0);
        assert_eq!(pool.token_1, Some(token_1));
        assert_eq!(pool.reserve_0, Amount::ZERO);
        assert_eq!(pool.reserve_1, Amount::ZERO);

        pool.reserve_0 = Amount::ONE;
        pool.reserve_1 = Amount::from_str("21.2342").unwrap();

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

        let (amount_0, amount_1) = pool
            .try_calculate_swap_amount_pair(
                Amount::from_tokens(20),
                Amount::from_tokens(30),
                None,
                None,
            )
            .unwrap();
        assert_eq!(amount_0, Amount::from_str("1.412815175518738639").unwrap());
        assert_eq!(amount_1, Amount::from_str("30").unwrap());

        let (amount_0, amount_1) = pool
            .try_calculate_liquidity_amount_pair(
                Amount::from_tokens(20),
                Amount::from_tokens(30),
                None,
                None,
            )
            .unwrap();
        assert_eq!(amount_0, Amount::from_str("0.666666666666666666").unwrap());
        assert_eq!(amount_1, Amount::from_str("14.156133333333333333").unwrap());

        let liquidity = pool.calculate_liquidity(
            Amount::from_tokens(30),
            Amount::from_str("1.412815175518738639").unwrap(),
            Amount::from_tokens(30),
        );
        assert_eq!(
            liquidity,
            Amount::from_str("42.384455265562159158").unwrap()
        );
    }

    #[test]
    fn test_pool_with_real_initial_liquidity() {
        let _ = env_logger::builder().is_test(true).try_init();

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

        assert_eq!(pool.token_0, token_0);
        assert_eq!(pool.token_1, Some(token_1));
        assert_eq!(pool.reserve_0, Amount::ZERO);
        assert_eq!(pool.reserve_1, Amount::ZERO);

        pool.reserve_0 = Amount::ONE;
        pool.reserve_1 = Amount::from_str("21.2342").unwrap();

        let (amount_0, amount_1) = pool
            .try_calculate_swap_amount_pair(
                Amount::from_tokens(20),
                Amount::from_tokens(30),
                None,
                None,
            )
            .unwrap();
        assert_eq!(amount_0, Amount::from_str("1.412815175518738639").unwrap());
        assert_eq!(amount_1, Amount::from_str("30").unwrap());

        let swap_amount_0 = pool.calculate_swap_amount_0(Amount::ONE).unwrap();
        assert_eq!(
            swap_amount_0,
            Amount::from_str("0.044846881859728669").unwrap()
        );

        let swap_amount_1 = pool.calculate_swap_amount_1(Amount::ONE).unwrap();
        assert_eq!(
            swap_amount_1,
            Amount::from_str("10.601150425638457686").unwrap()
        );

        let (amount_0, amount_1) = pool
            .try_calculate_liquidity_amount_pair(
                Amount::from_tokens(20),
                Amount::from_tokens(30),
                None,
                None,
            )
            .unwrap();
        assert_eq!(amount_0, Amount::from_str("0.666666666666666666").unwrap());
        assert_eq!(amount_1, Amount::from_str("14.156133333333333333").unwrap());

        let liquidity = pool.calculate_liquidity(
            Amount::from_tokens(30),
            Amount::from_str("1.412815175518738639").unwrap(),
            Amount::from_tokens(30),
        );
        assert_eq!(
            liquidity,
            Amount::from_str("42.384455265562159158").unwrap()
        );

        let (price_0, price_1) = pool.calculate_price_pair();
        assert_eq!(price_0, Amount::from_str("21.2342").unwrap());
        assert_eq!(price_1, Amount::from_str("0.047093839183957955").unwrap());
    }

    #[test]
    fn test_pool_mint_fee_matches_uniswap_v2_formula() {
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
        pool.reserve_0 = Amount::from_tokens(121);
        pool.reserve_1 = Amount::from_tokens(121);
        pool.k_last = Amount::from_tokens(100);

        assert_eq!(
            pool.mint_fee(Amount::from_tokens(100)),
            Amount::from_str("2.978723404255319148").unwrap(),
        );
    }
}
