use crate::store_type::StoreType;
use async_graphql::{Enum, Request, Response, SimpleObject};
use linera_sdk::{
    graphql::GraphQLMutationRoot,
    linera_base_types::{Account, ApplicationId, ContractAbi, CryptoHash, ServiceAbi, Timestamp},
};
use serde::{Deserialize, Serialize};

pub struct BlobGatewayAbi;

impl ContractAbi for BlobGatewayAbi {
    type Operation = BlobGatewayOperation;
    type Response = BlobGatewayResponse;
}

impl ServiceAbi for BlobGatewayAbi {
    type Query = Request;
    type QueryResponse = Response;
}

#[derive(Debug, Deserialize, Serialize, Clone, Eq, PartialEq, Enum, Copy)]
#[serde(rename_all = "UPPERCASE")]
pub enum BlobDataType {
    Image,
    Video,
    Html,
    Raw,
}

#[derive(Debug, Deserialize, Serialize, Clone, SimpleObject, Eq, PartialEq)]
#[serde(rename_all = "camelCase")]
pub struct BlobData {
    pub store_type: StoreType,
    pub data_type: BlobDataType,
    pub blob_hash: CryptoHash,
    pub creator: Account,
    pub created_at: Timestamp,
}

#[derive(Debug, Deserialize, Serialize, GraphQLMutationRoot)]
pub enum BlobGatewayOperation {
    SetOperator {
        new_operator: Account,
    },
    Register {
        store_type: StoreType,
        data_type: BlobDataType,
        blob_hash: CryptoHash,
    },
    AppendState {
        state_application_id: ApplicationId,
    },
    Handoff {
        new_business_application_id: ApplicationId,
    },
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub enum BlobGatewayMessage {
    Register { blob_data: BlobData },
}

#[derive(Debug, Deserialize, Serialize, Default)]
pub enum BlobGatewayResponse {
    #[default]
    Ok,
}
