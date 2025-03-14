use crate::store_type::StoreType;
use async_graphql::scalar;
use linera_sdk::{
    graphql::GraphQLMutationRoot,
    linera_base_types::{Account, ApplicationId, Ed25519Signature, Timestamp},
};
use serde::{Deserialize, Serialize};

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
pub struct InstantiationArgument {
    pub application_types: Vec<String>,
}

#[derive(Debug, Clone, Deserialize, Serialize, Eq, PartialEq)]
pub struct Metadata {
    pub creator: Option<Account>,
    pub application_name: String,
    pub application_id: ApplicationId,
    // Preset application types could be added by operator
    pub application_type: String,
    pub key_words: Vec<String>,
    pub logo_store_type: StoreType,
    pub logo: String,
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
