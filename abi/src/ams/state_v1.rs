use super::abi::Metadata;
use async_graphql::{Request, Response};
use linera_sdk::linera_base_types::{Account, ApplicationId, ContractAbi, ServiceAbi};
use serde::{Deserialize, Serialize};

pub struct AmsStateAbi;

impl ContractAbi for AmsStateAbi {
    type Operation = AmsStateOperation;
    type Response = AmsStateResponse;
}

impl ServiceAbi for AmsStateAbi {
    type Query = Request;
    type QueryResponse = Response;
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
pub struct StateInstantiationArgument {
    pub business_application_id: ApplicationId,
    pub operator: Option<Account>,
}

#[derive(Debug, Clone, Deserialize, Eq, PartialEq, Serialize)]
pub enum AmsStateOperation {
    Bootstrap,
    SetOperator {
        new_operator: Account,
    },
    AddApplicationType {
        owner: Account,
        application_type: String,
    },
    RegisterApplication {
        metadata: Metadata,
    },
    ClaimApplication {
        owner: Account,
        application_id: ApplicationId,
    },
    UpdateApplication {
        owner: Account,
        application_id: ApplicationId,
        metadata: Metadata,
    },
    Application {
        application_id: ApplicationId,
    },
    Handoff {
        new_business_application_id: ApplicationId,
    },
}

#[derive(Debug, Clone, Deserialize, Eq, PartialEq, Serialize)]
pub enum AmsStateResponse {
    Ok,
    Application(Option<Metadata>),
}
