use serde::{de::DeserializeOwned, Serialize};

pub trait StateKey {
    fn into_state_key(&self) -> Result<Vec<u8>, bcs::Error>;
}

impl<T> StateKey for T
where
    T: Serialize,
{
    fn into_state_key(&self) -> Result<Vec<u8>, bcs::Error> {
        bcs::to_bytes(self)
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
