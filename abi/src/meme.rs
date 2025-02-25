use crate::store_type::StoreType;
use async_graphql::scalar;
use async_graphql::InputObject;
use linera_sdk::base::{Amount, ApplicationId};
use serde::{Deserialize, Serialize};

#[derive(Default, Debug, Clone, Deserialize, Serialize, Eq, PartialEq, InputObject)]
pub struct Metadata {
    pub logo_store_type: StoreType,
    pub logo: String,
    pub description: String,
    pub twitter: Option<String>,
    pub telegram: Option<String>,
    pub discord: Option<String>,
    pub website: Option<String>,
    pub github: Option<String>,
}

#[derive(Debug, Clone, Deserialize, Serialize, Eq, PartialEq, InputObject)]
pub struct Mint {
    pub initial_currency: Amount,
    pub fixed_currency: bool,
}

#[derive(Default, Debug, Clone, Deserialize, Serialize, Eq, PartialEq, InputObject)]
pub struct Meme {
    pub initial_supply: Amount,
    pub total_supply: Amount,
    pub name: String,
    pub ticker: String,
    pub decimals: u8,
    pub metadata: Metadata,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize, InputObject)]
pub struct InstantiationArgument {
    pub meme: Meme,
    pub mint: Option<Mint>,
    pub fee_percent: Option<Amount>,
    pub blob_gateway_application_id: Option<ApplicationId>,
    pub ams_application_id: Option<ApplicationId>,
    pub swap_application_id: Option<ApplicationId>,
    pub proxy_application_id: Option<ApplicationId>,
}

#[derive(Clone, Copy, Debug, Deserialize, Serialize)]
pub struct Parameters {}

scalar!(Parameters);
