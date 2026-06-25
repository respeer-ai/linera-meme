use crate::state_key::{StateKey, StateValue};
use async_trait::async_trait;

#[async_trait(?Send)]
pub trait StateServiceInterface {
    type Error: std::fmt::Debug + std::error::Error + 'static;

    async fn read<K, V>(&self, key: &K) -> Result<Option<V>, Self::Error>
    where
        K: StateKey,
        V: StateValue;

    async fn batch_read<K, V>(&self, keys: &[K]) -> Result<Vec<Option<V>>, Self::Error>
    where
        K: StateKey,
        V: StateValue;
}
