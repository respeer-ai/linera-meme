use serde::{Deserialize, Serialize};

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
