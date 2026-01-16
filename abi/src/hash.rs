use linera_sdk::linera_base_types::CryptoHash;
use num_bigint::BigUint;
use num_traits::One;
use std::cmp::Ordering;

pub fn hash_to_u256(hash: CryptoHash) -> BigUint {
    BigUint::from_bytes_be(&hash.as_bytes().0)
}

pub fn hash_cmp(hash1: CryptoHash, hash2: CryptoHash) -> Ordering {
    let hash1_bigint = hash_to_u256(hash1);
    let hash2_bigint = hash_to_u256(hash2);

    hash1_bigint.cmp(&hash2_bigint)
}

fn u256_to_hash(value: BigUint) -> CryptoHash {
    let mut bytes = value.to_bytes_be();

    if bytes.len() > 32 {
        bytes = bytes[bytes.len() - 32..].to_vec();
    } else if bytes.len() < 32 {
        let mut padded = vec![0u8; 32 - bytes.len()];
        padded.extend(bytes);
        bytes = padded;
    }

    let mut arr = [0u8; 32];
    arr.copy_from_slice(&bytes);

    CryptoHash::from(arr)
}

pub fn hash_increment(hash: CryptoHash) -> CryptoHash {
    let mut value = hash_to_u256(hash);
    value += BigUint::one();
    u256_to_hash(value)
}
