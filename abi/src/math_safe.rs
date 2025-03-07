use crate::big_amount::BigAmount;
use linera_sdk::linera_base_types::Amount;
use num_bigint::BigUint;
use num_traits::{cast::ToPrimitive, FromPrimitive};
use std::ops::{Add, Div, Mul};

pub fn sqrt(amount: Amount) -> Amount {
    Amount::from_attos(
        BigUint::sqrt(&BigUint::from_u128(u128::from(amount)).expect("Couldn't convert amount"))
            .to_u128()
            .expect("Couldn't convert BigUint"),
    )
}

pub fn mul(amount_1: Amount, amount_2: Amount) -> BigUint {
    let _amount_1 = BigUint::from_u128(u128::from(amount_1)).expect("Couldn't convert amount");
    let _amount_2 = BigUint::from_u128(u128::from(amount_2)).expect("Couldn't convert amount");
    _amount_1.mul(_amount_2)
}

pub fn mul_percent_10000(amount_1: Amount, percent: u16) -> Amount {
    let _amount_1 = BigUint::from_u128(u128::from(amount_1)).expect("Couldn't convert amount");
    let _percent = BigUint::from_u16(percent).expect("Couldn't convert amount");
    let _hundred = BigUint::from_u16(10000).expect("Couldn't convert amount");
    Amount::from_attos(
        _amount_1
            .mul(_percent)
            .div(_hundred)
            .to_u128()
            .expect("Couldn't convert BigUint"),
    )
}

pub fn mul_then_div(amount_1: Amount, amount_2: Amount, amount_3: Amount) -> Amount {
    let _amount_1 = BigUint::from_u128(u128::from(amount_1)).expect("Couldn't convert amount");
    let _amount_2 = BigUint::from_u128(u128::from(amount_2)).expect("Couldn't convert amount");
    let _amount_3 = BigUint::from_u128(u128::from(amount_3)).expect("Couldn't convert amount");
    Amount::from_attos(
        _amount_1
            .mul(_amount_2)
            .div(_amount_3)
            .to_u128()
            .expect("Couldn't convert BigUint"),
    )
}

pub fn mul_then_sqrt(amount_1: Amount, amount_2: Amount) -> Amount {
    let _amount_1 = BigUint::from_u128(u128::from(amount_1)).expect("Couldn't convert amount");
    let _amount_2 = BigUint::from_u128(u128::from(amount_2)).expect("Couldn't convert amount");
    Amount::from_attos(
        BigUint::sqrt(&_amount_1.mul(_amount_2))
            .to_u128()
            .expect("Couldn't convert BigUint"),
    )
}

pub fn mul_then_add(amount_1: Amount, amount_2: Amount, amount_3: Amount) -> Amount {
    let _amount_1 = BigUint::from_u128(u128::from(amount_1)).expect("Couldn't convert amount");
    let _amount_2 = BigUint::from_u128(u128::from(amount_2)).expect("Couldn't convert amount");
    let _amount_3 = BigUint::from_u128(u128::from(amount_3)).expect("Couldn't convert amount");
    Amount::from_attos(
        _amount_1
            .mul(_amount_2)
            .add(_amount_3)
            .to_u128()
            .expect("Couldn't convert BigUint"),
    )
}

pub fn div_then_mul_to_big_amount(divisor: Amount, dividend: Amount, extra: Amount) -> BigAmount {
    let _divisor = BigUint::from_u128(u128::from(divisor)).expect("Couldn't convert amount");
    let _dividend = BigUint::from_u128(u128::from(dividend)).expect("Couldn't convert amount");
    let _extra = BigUint::from_u128(u128::from(extra)).expect("Couldn't convert amount");
    BigAmount(_divisor.mul(_extra).div(_dividend))
}
