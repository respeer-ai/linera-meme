use async_graphql::{Request, Response};
use linera_sdk::linera_base_types::{Account, ApplicationId, ContractAbi, ServiceAbi};
use serde::{de::DeserializeOwned, Deserialize, Serialize};

pub struct StateAbi;

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

pub struct BatchWrite {
    writes: Vec<(Vec<u8>, Vec<u8>)>,
}

impl BatchWrite {
    pub fn new() -> Self {
        Self { writes: Vec::new() }
    }

    pub fn put<K, V>(&mut self, key: &K, value: &V) -> Result<(), bcs::Error>
    where
        K: Serialize,
        V: StateValue,
    {
        self.writes
            .push((bcs::to_bytes(key)?, value.into_state_bytes()?));
        Ok(())
    }

    pub fn into_writes(self) -> Vec<(Vec<u8>, Vec<u8>)> {
        self.writes
    }
}

impl Default for BatchWrite {
    fn default() -> Self {
        Self::new()
    }
}

impl ContractAbi for StateAbi {
    type Operation = StateOperation;
    type Response = StateResponse;
}

impl ServiceAbi for StateAbi {
    type Query = Request;
    type QueryResponse = Response;
}

#[derive(Debug, Clone, Deserialize, Eq, PartialEq, Serialize)]
pub enum StateOperation {
    InitializeOperator {
        operator: Account,
    },
    CreateNamespace {
        namespace: u8,
    },
    Read {
        namespace: u8,
        key: Vec<u8>,
    },
    Write {
        namespace: u8,
        key: Vec<u8>,
        value: Vec<u8>,
    },
    Delete {
        namespace: u8,
        key: Vec<u8>,
    },
    BatchRead {
        namespace: u8,
        keys: Vec<Vec<u8>>,
    },
    BatchWrite {
        namespace: u8,
        writes: Vec<(Vec<u8>, Vec<u8>)>,
    },
    BatchDelete {
        namespace: u8,
        keys: Vec<Vec<u8>>,
    },
    FreezeNamespace {
        application_id: ApplicationId,
    },
    UnfreezeNamespace {
        application_id: ApplicationId,
    },
    Handoff {
        application_id: ApplicationId,
        namespace: u8,
        new_application_id: ApplicationId,
    },
    SetOperator {
        application_id: ApplicationId,
        new_operator: Account,
    },
}

#[derive(Debug, Clone, Deserialize, Eq, PartialEq, Serialize)]
pub enum StateMessage {
    FreezeNamespace,
    UnfreezeNamespace,
    Handoff {
        application_id: ApplicationId,
        namespace: u8,
        new_application_id: ApplicationId,
    },
    SetOperator {
        new_operator: Account,
    },
}

#[derive(Debug, Clone, Deserialize, Eq, PartialEq, Serialize)]
pub enum StateResponse {
    Ok,
    Read(Option<Vec<u8>>),
    BatchRead(Vec<Option<Vec<u8>>>),
}
