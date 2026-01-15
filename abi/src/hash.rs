use linera_sdk::linera_base_types::CryptoHash;
use num_bigint::BigUint;
use std::cmp::Ordering;

pub fn hash_to_u256(hash: CryptoHash) -> BigUint {
    BigUint::from_bytes_be(&hash.as_bytes().0)
}

pub fn hash_cmp(hash1: CryptoHash, hash2: CryptoHash) -> Ordering {
    let hash1_bigint = hash_to_u256(hash1);
    let hash2_bigint = hash_to_u256(hash2);

    hash1_bigint.cmp(&hash2_bigint)
}
