use super::BlobData;
use async_graphql::{Request, Response};
use linera_sdk::linera_base_types::{Account, ApplicationId, ContractAbi, CryptoHash, ServiceAbi};
use serde::{Deserialize, Serialize};

pub struct BlobGatewayStateAbi;

impl ContractAbi for BlobGatewayStateAbi {
    type Operation = BlobGatewayStateV1Operation;
    type Response = BlobGatewayStateV1Response;
}

impl ServiceAbi for BlobGatewayStateAbi {
    type Query = Request;
    type QueryResponse = Response;
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
pub struct StateInstantiationArgument {
    pub business_application_id: ApplicationId,
    pub operator: Option<Account>,
}

#[derive(Debug, Clone, Deserialize, Eq, PartialEq, Serialize)]
pub enum BlobGatewayStateV1Operation {
    Handoff {
        new_business_application_id: ApplicationId,
    },
    CreateBlob {
        blob_data: BlobData,
    },
    Blob {
        blob_hash: CryptoHash,
    },
    Blobs,
}

#[derive(Debug, Clone, Deserialize, Eq, PartialEq, Serialize)]
pub enum BlobGatewayStateV1Response {
    Ok,
    Blob(Option<BlobData>),
    Blobs(Vec<BlobData>),
}
