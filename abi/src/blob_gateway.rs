use crate::store_type::StoreType;
use async_graphql::{Enum, Request, Response, SimpleObject};
use linera_sdk::{
    graphql::GraphQLMutationRoot,
    linera_base_types::{Account, ContractAbi, CryptoHash, ServiceAbi, Timestamp},
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
pub enum BlobDataType {
    Image,
    Video,
    Html,
    Raw,
}

#[derive(Debug, Deserialize, Serialize, Clone, SimpleObject, Eq, PartialEq)]
pub struct BlobData {
    pub store_type: StoreType,
    pub data_type: BlobDataType,
    pub blob_hash: CryptoHash,
    pub created_at: Timestamp,
    pub creator: Account,
}

#[derive(Debug, Deserialize, Serialize, GraphQLMutationRoot)]
pub enum BlobGatewayOperation {
    Register {
        store_type: StoreType,
        data_type: BlobDataType,
        blob_hash: CryptoHash,
    },
}

#[derive(Debug, Deserialize, Serialize, Default)]
pub enum BlobGatewayResponse {
    #[default]
    Ok,
}
