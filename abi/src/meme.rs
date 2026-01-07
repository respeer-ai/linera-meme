use crate::store_type::StoreType;
use async_graphql::{scalar, InputObject, Request, Response, SimpleObject};
use linera_sdk::{
    graphql::GraphQLMutationRoot,
    linera_base_types::{
        Account, Amount, ApplicationId, BlockHeight, ChainId, ContractAbi, CryptoHash, ServiceAbi,
        TimeDelta,
    },
};
use serde::{Deserialize, Serialize};

#[derive(
    Default, Debug, Clone, Deserialize, Serialize, Eq, PartialEq, InputObject, SimpleObject,
)]
#[serde(rename_all = "camelCase")]
pub struct Metadata {
    pub logo_store_type: StoreType,
    pub logo: Option<CryptoHash>,
    pub description: String,
    pub twitter: Option<String>,
    pub telegram: Option<String>,
    pub discord: Option<String>,
    pub website: Option<String>,
    pub github: Option<String>,
    pub live_stream: Option<String>,
}

#[derive(Debug, Clone, Deserialize, Serialize, Eq, PartialEq)]
#[serde(rename_all = "camelCase")]
pub struct Liquidity {
    pub fungible_amount: Amount,
    pub native_amount: Amount,
}

scalar!(Liquidity);

#[derive(
    Default, Debug, Clone, Deserialize, Serialize, Eq, PartialEq, InputObject, SimpleObject,
)]
#[serde(rename_all = "camelCase")]
pub struct Meme {
    pub initial_supply: Amount,
    pub total_supply: Amount,
    pub name: String,
    pub ticker: String,
    pub decimals: u8,
    pub metadata: Metadata,
    pub virtual_initial_liquidity: bool,
    pub initial_liquidity: Option<Liquidity>,
}

#[derive(Default, Clone, Debug, Deserialize, Eq, PartialEq, Serialize, InputObject)]
pub struct InstantiationArgument {
    pub meme: Meme,
    pub blob_gateway_application_id: Option<ApplicationId>,
    pub ams_application_id: Option<ApplicationId>,
    pub proxy_application_id: Option<ApplicationId>,
    pub swap_application_id: Option<ApplicationId>,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize, SimpleObject)]
pub struct MiningInfo {
    /// Mining hash = sha256sum(block_height, nonce, chain_id, signer, /* previous_block_hash */)
    /// Mine opeartion must be the last operation of the block
    /// new_target = target * (block_duration / target_block_duration)
    /// difficulty = initial_target / new_target
    pub initial_target: CryptoHash,
    pub target: CryptoHash,
    pub new_target: CryptoHash,
    pub block_duration: TimeDelta,
    pub target_block_duration: TimeDelta,
    pub target_adjustment_blocks: u16,
    /// If the block only have Mine operation, then it'll get only part of reward
    pub empty_block_reward_percent: u8,

    /// Current block processing
    pub mining_height: BlockHeight,
    pub mining_executions: usize,
    // We're not able to get block hash from SDK so we ignore it right now
    // pub previous_block_hash: CryptoHash,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct MemeParameters {
    pub creator: Account,
    pub initial_liquidity: Option<Liquidity>,
    pub virtual_initial_liquidity: bool,
    // TODO: work around for https://github.com/linera-io/linera-protocol/issues/3538
    pub swap_creator_chain_id: ChainId,

    pub enable_mining: bool,
    pub mining_supply: Option<Amount>,
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
    CreatorChainId,

    Transfer {
        to: Account,
        amount: Amount,
    },
    TransferFrom {
        from: Account,
        to: Account,
        amount: Amount,
    },
    TransferFromApplication {
        to: Account,
        amount: Amount,
    },
    // Special operation used by swap to initialize liquidity for new pool
    InitializeLiquidity {
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
        amount: Amount,
    },
    Mint {
        to: Account,
        amount: Amount,
    },
}

#[derive(Clone, Debug, Deserialize, Serialize)]
pub enum MemeMessage {
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
    // Special operation used by swap to initialize liquidity for new pool
    InitializeLiquidity {
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
    Mint {
        to: Account,
        amount: Amount,
    },
}

#[derive(Debug, Deserialize, Serialize, Default)]
pub enum MemeResponse {
    #[default]
    Ok,
    Fail(String),
    ChainId(ChainId),
}
