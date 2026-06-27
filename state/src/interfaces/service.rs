use abi::state::StateValue;
use serde::Serialize;

pub trait StateServiceInterface {
    type Error: std::fmt::Debug + std::error::Error + 'static;

    fn read<K, V>(&self, key: &K) -> Result<Option<V>, Self::Error>
    where
        K: Serialize,
        V: StateValue;

    // Batch reads are homogeneous: every key in `keys` must decode to the same `V`.
    // Do not mix enum key variants that map to different value types in one call.
    fn batch_read<K, V>(&self, keys: &[K]) -> Result<Vec<Option<V>>, Self::Error>
    where
        K: Serialize,
        V: StateValue;
}
