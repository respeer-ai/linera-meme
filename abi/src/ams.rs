use crate::store_type::StoreType;
use async_graphql::{scalar, Request, Response};
use linera_sdk::{
    graphql::GraphQLMutationRoot,
    linera_base_types::{
        Account, ApplicationId, ContractAbi, CryptoHash, Ed25519Signature, ServiceAbi, Timestamp,
    },
};
use serde::{Deserialize, Serialize};

pub struct AmsAbi;

impl ContractAbi for AmsAbi {
    type Operation = AmsOperation;
    type Response = AmsResponse;
}

impl ServiceAbi for AmsAbi {
    type Query = Request;
    type QueryResponse = Response;
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
pub struct InstantiationArgument {
    pub application_types: Vec<String>,
}

pub const MEME: &str = "Meme";
pub const MEME_PROXY: &str = "MemeProxy";
pub const SWAP: &str = "Swap";
pub const AMS: &str = "Ams";
pub const BLOB_GATEWAY: &str = "BlobGateway";
pub const LIQUIDITY_POOL: &str = "LiquidityPool";
pub const GAME: &str = "Game";
pub const SOCIAL: &str = "Social";
pub const DEFI: &str = "DeFi";
pub const UTILITY: &str = "Utility";
pub const OTHER: &str = "Other";

pub const APPLICATION_TYPES: &'static [&'static str] = &[
    MEME,
    MEME_PROXY,
    SWAP,
    AMS,
    BLOB_GATEWAY,
    LIQUIDITY_POOL,
    GAME,
    SOCIAL,
    DEFI,
    UTILITY,
    OTHER,
];

#[derive(Debug, Clone, Deserialize, Serialize, Eq, PartialEq)]
pub struct Metadata {
    pub creator: Account,
    pub application_name: String,
    pub application_id: ApplicationId,
    // Preset application types could be added by operator
    pub application_type: String,
    pub key_words: Vec<String>,
    pub logo_store_type: StoreType,
    pub logo: CryptoHash,
    pub description: String,
    pub twitter: Option<String>,
    pub telegram: Option<String>,
    pub discord: Option<String>,
    pub website: Option<String>,
    pub github: Option<String>,
    /// JSON spec of registered application
    pub spec: Option<String>,
    pub created_at: Timestamp,
}

scalar!(Metadata);

#[derive(Debug, Deserialize, Serialize, GraphQLMutationRoot)]
pub enum AmsOperation {
    Register {
        metadata: Metadata,
    },
    // Claim exists application with the same owner as creator
    Claim {
        application_id: ApplicationId,
        signature: Ed25519Signature,
    },
    AddApplicationType {
        application_type: String,
    },
    Update {
        application_id: ApplicationId,
        metadata: Metadata,
    },
}

#[derive(Debug, Deserialize, Serialize, Default)]
pub enum AmsResponse {
    #[default]
    Ok,
}
