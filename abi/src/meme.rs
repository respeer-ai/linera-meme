use crate::store_type::StoreType;
use async_graphql::{scalar, InputObject, Request, Response, SimpleObject};
use linera_sdk::{
    graphql::GraphQLMutationRoot,
    linera_base_types::{
        Account, Amount, ApplicationId, ChainId, ContractAbi, CryptoHash, ServiceAbi,
    },
};
use serde::{Deserialize, Serialize};

#[derive(
    Default, Debug, Clone, Deserialize, Serialize, Eq, PartialEq, InputObject, SimpleObject,
)]
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

#[derive(
    Default, Debug, Clone, Deserialize, Serialize, Eq, PartialEq, InputObject, SimpleObject,
)]
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
    pub blob_gateway_application_id: Option<ApplicationId>,
    pub ams_application_id: Option<ApplicationId>,
    pub proxy_application_id: Option<ApplicationId>,
    pub swap_application_id: Option<ApplicationId>,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
pub struct MemeParameters {
    pub creator: Account,
    pub initial_liquidity: Option<Liquidity>,
    pub virtual_initial_liquidity: bool,
}

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
    // Work around before https://github.com/linera-io/linera-protocol/pull/3382 being merged
    // Can only initialize liquidity which is already defined when create token
    InitializeLiquidity,
    Transfer {
        to: Account,
        amount: Amount,
    },
    TransferFrom {
        from: Account,
        to: Account,
        amount: Amount,
    },
    // Special operation used by swap application only
    TransferFromApplication {
        to: Account,
        amount: Amount,
    },
    Approve {
        spender: Account,
        amount: Amount,
    },
    TransferOwnership {
        new_owner: Account,
    },
    Mine {
        nonce: CryptoHash,
    },
    // Only be run on meme chain
    TransferToCaller {
        transfer_id: u64,
        amount: Amount,
    },
    // Return creator chain to caller
    CreatorChainId,
}

#[derive(Debug, Deserialize, Serialize)]
pub enum MemeMessage {
    // Work around before https://github.com/linera-io/linera-protocol/pull/3382 being merged
    InitializeLiquidity {
        operator: Account,
    },
    LiquidityFunded,
    Transfer {
        from: Account,
        to: Account,
        amount: Amount,
    },
    TransferFrom {
        owner: Account,
        from: Account,
        to: Account,
        amount: Amount,
    },
    TransferFromApplication {
        caller: Account,
        to: Account,
        amount: Amount,
    },
    Approve {
        owner: Account,
        spender: Account,
        amount: Amount,
    },
    TransferOwnership {
        owner: Account,
        new_owner: Account,
    },
    // Mine is only run on creation chain so we don't need a message
}

#[derive(Debug, Deserialize, Serialize, Default)]
pub enum MemeResponse {
    #[default]
    Ok,
    Fail(String),
    ChainId(ChainId),
}
