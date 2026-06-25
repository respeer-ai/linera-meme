use async_graphql::{Request, Response};
use linera_sdk::linera_base_types::{Account, ApplicationId, ContractAbi, ServiceAbi};
use serde::{Deserialize, Serialize};

pub struct StateAbi;

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
    InitializeOperator,
    CreateNamespace {
        namespace: u8,
    },
    FreezeNamespace,
    UnfreezeNamespace,
    Handoff {
        namespace: u8,
        new_application_id: ApplicationId,
    },
    BatchRead {
        namespace: u8,
        keys: Vec<Vec<u8>>,
    },
    BatchWrite {
        namespace: u8,
        writes: Vec<(Vec<u8>, Option<Vec<u8>>)>,
    },
    SetOperator {
        new_operator: Account,
    },
}

#[derive(Debug, Clone, Deserialize, Eq, PartialEq, Serialize)]
pub enum StateResponse {
    Ok,
    BatchRead(Vec<Option<Vec<u8>>>),
}
