use crate::store_type::StoreType;
use async_graphql::{scalar, InputObject, Request, Response};
use linera_sdk::{
    base::{
        Account, AccountOwner, Amount, ApplicationId, ContractAbi, CryptoHash, Owner, ServiceAbi,
    },
    graphql::GraphQLMutationRoot,
};
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
pub struct Liquidity {
    pub fungible_amount: Amount,
    pub native_amount: Amount,
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
    pub initial_liquidity: Liquidity,
    pub blob_gateway_application_id: Option<ApplicationId>,
    pub ams_application_id: Option<ApplicationId>,
    pub proxy_application_id: Option<ApplicationId>,
    pub swap_application_id: Option<ApplicationId>,
    pub virtual_initial_liquidity: bool,
}

#[derive(Clone, Copy, Debug, Deserialize, Serialize)]
pub struct MemeParameters {}

scalar!(MemeParameters);

pub struct MemeAbi;

impl ContractAbi for MemeAbi {
    type Operation = MemeOperation;
    type Response = MemeResponse;
}

impl ServiceAbi for MemeAbi {
    type Query = Request;
    type QueryResponse = Response;
}

#[derive(Debug, Deserialize, Serialize, GraphQLMutationRoot)]
pub enum MemeOperation {
    Transfer {
        to: AccountOwner,
        amount: Amount,
    },
    TransferFrom {
        from: AccountOwner,
        to: AccountOwner,
        amount: Amount,
    },
    Approve {
        spender: AccountOwner,
        amount: Amount,
        rfq_application: Option<Account>,
    },
    TransferOwnership {
        new_owner: Owner,
    },
    Mine {
        nonce: CryptoHash,
    },
}

#[derive(Debug, Deserialize, Serialize)]
pub enum MemeMessage {
    Transfer {
        to: AccountOwner,
        amount: Amount,
    },
    TransferFrom {
        from: AccountOwner,
        to: AccountOwner,
        amount: Amount,
    },
    Approve {
        spender: AccountOwner,
        amount: Amount,
        rfq_application: Option<Account>,
    },
    Approved {
        rfq_application: ApplicationId,
    },
    Rejected {
        rfq_application: ApplicationId,
    },
    TransferOwnership {
        new_owner: Owner,
    },
    // Mine is only run on creation chain so we don't need a message
}

#[derive(Debug, Deserialize, Serialize, Default)]
pub enum MemeResponse {
    #[default]
    Ok,
}
