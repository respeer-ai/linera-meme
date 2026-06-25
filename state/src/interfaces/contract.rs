use crate::state_key::{StateKey, StateValue};
use async_trait::async_trait;
use linera_sdk::linera_base_types::ApplicationId;

#[async_trait(?Send)]
pub trait StateContractInterface {
    type Error: std::fmt::Debug + std::error::Error + 'static;

    async fn initialize_operator(&mut self) -> Result<(), Self::Error>;

    async fn create_namespace(&mut self) -> Result<(), Self::Error>;

    async fn freeze_namespace(&mut self) -> Result<(), Self::Error>;

    async fn unfreeze_namespace(&mut self) -> Result<(), Self::Error>;

    async fn handoff(&mut self, new_application_id: ApplicationId) -> Result<(), Self::Error>;

    async fn read<K, V>(&mut self, key: &K) -> Result<Option<V>, Self::Error>
    where
        K: StateKey,
        V: StateValue;

    async fn batch_read<K, V>(&mut self, keys: &[K]) -> Result<Vec<Option<V>>, Self::Error>
    where
        K: StateKey,
        V: StateValue;

    async fn write<K, V>(&mut self, key: &K, value: &V) -> Result<(), Self::Error>
    where
        K: StateKey,
        V: StateValue;

    async fn batch_write<K, V>(&mut self, writes: &[(K, Option<V>)]) -> Result<(), Self::Error>
    where
        K: StateKey,
        V: StateValue;

    async fn delete<K>(&mut self, key: &K) -> Result<(), Self::Error>
    where
        K: StateKey;
}
