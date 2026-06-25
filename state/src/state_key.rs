use serde::{de::DeserializeOwned, Deserialize, Serialize};

#[derive(Clone, Debug, Deserialize, Eq, Hash, Ord, PartialEq, PartialOrd, Serialize)]
pub struct StateKey(Vec<u8>);

impl StateKey {
    pub fn new(namespace: u8, slot: u8, key: Vec<u8>) -> Self {
        let mut state_key = Vec::with_capacity(2 + key.len());
        state_key.push(namespace);
        state_key.push(slot);
        state_key.extend(key);
        Self(state_key)
    }

    pub fn into_bytes(self) -> Vec<u8> {
        self.0
    }
}

pub trait StateValue: Sized {
    fn into_state_bytes(&self) -> Result<Vec<u8>, bcs::Error>;

    fn from_state_bytes(bytes: &[u8]) -> Result<Self, bcs::Error>;
}

impl<T> StateValue for T
where
    T: Serialize + DeserializeOwned,
{
    fn into_state_bytes(&self) -> Result<Vec<u8>, bcs::Error> {
        bcs::to_bytes(self)
    }

    fn from_state_bytes(bytes: &[u8]) -> Result<Self, bcs::Error> {
        bcs::from_bytes(bytes)
    }
}
