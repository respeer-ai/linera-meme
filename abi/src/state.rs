use async_graphql::{Request, Response};
use linera_sdk::linera_base_types::{Account, ApplicationId, ContractAbi, ServiceAbi};
use serde::{Deserialize, Serialize};

pub struct StateAbi;
pub trait StateBaseInterface {
    type Error: std::fmt::Debug + std::error::Error + 'static;

    fn state_app_id(&mut self) -> Result<ApplicationId, Self::Error>;

    fn state_namespace(&mut self) -> Result<u8, Self::Error>;
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
