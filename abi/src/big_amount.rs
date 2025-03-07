use async_graphql::scalar;
use linera_sdk::linera_base_types::Amount;
use num_bigint::BigUint;
use num_traits::{cast::ToPrimitive, FromPrimitive};
use serde::{Deserialize, Deserializer, Serialize, Serializer};
use std::{
    ops::{Add, Div, Mul, Sub},
    str::FromStr,
};

#[derive(Debug, Clone, Eq, PartialEq, Default)]
pub struct BigAmount(pub BigUint);

impl BigAmount {
    pub fn add(self, amount: BigAmount) -> BigAmount {
        BigAmount(self.0.add(amount.0))
    }

    pub fn sub(self, amount: BigAmount) -> BigAmount {
        BigAmount(self.0.sub(amount.0))
    }

    pub fn div(self, amount: BigAmount) -> BigAmount {
        BigAmount(self.0.div(amount.0))
    }

    pub fn mul(self, amount: BigAmount) -> BigAmount {
        BigAmount(self.0.mul(amount.0))
    }
}

impl Into<Amount> for BigAmount {
    fn into(self) -> Amount {
        Amount::from_attos(self.0.to_u128().expect("Couldn't convert BigUint"))
    }
}

impl From<Amount> for BigAmount {
    fn from(amount: Amount) -> BigAmount {
        BigAmount(BigUint::from_u128(u128::from(amount)).expect("Couldn't convert amount"))
    }
}

impl From<u128> for BigAmount {
    fn from(u: u128) -> BigAmount {
        BigAmount(BigUint::from_u128(u).expect("Couldn't convert number"))
    }
}

impl Serialize for BigAmount {
    fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: Serializer,
    {
        self.0.to_string().serialize(serializer)
    }
}

impl<'de> Deserialize<'de> for BigAmount {
    fn deserialize<D>(deserializer: D) -> Result<Self, D::Error>
    where
        D: Deserializer<'de>,
    {
        Ok(BigAmount(
            BigUint::from_str(&String::deserialize(deserializer)?)
                .expect("Couldn't convert BigUint"),
        ))
    }
}

scalar!(BigAmount);
