use crate::{big_amount::BigAmount, meme::Meme};
use async_graphql::{scalar, InputObject, Request, Response, SimpleObject};
use linera_sdk::{
    graphql::GraphQLMutationRoot,
    linera_base_types::{Account, Amount, ApplicationId, ContractAbi, ServiceAbi, Timestamp},
};
use serde::{Deserialize, Serialize};

pub struct PoolAbi;

impl ContractAbi for PoolAbi {
    type Operation = PoolOperation;
    type Response = PoolResponse;
}

impl ServiceAbi for PoolAbi {
    type Query = Request;
    type QueryResponse = Response;
}
#[derive(Debug, Copy, Clone, Deserialize, Serialize, GraphQLMutationRoot)]
pub enum PoolOperation {
    // Only for application creator to create pool with virtual initial liquidity
    CreatePool {
        token_0: ApplicationId,
        // None means add pair to native token
        token_1: Option<ApplicationId>,
        // Actual deposited initial liquidity
        // New listed token must not be 0
        amount_0: Amount,
        amount_1: Amount,
    },
    SetFeeTo {
        account: Account,
    },
    SetFeeToSetter {
        account: Account,
    },
    // TODO: AddLiquidity / RemoveLiquidity / Swap
}

#[derive(Debug, Deserialize, Serialize, Default)]
pub enum PoolResponse {
    #[default]
    Ok,
}

#[derive(Debug, Deserialize, Serialize)]
pub enum PoolMessage {
    // Only for application creator to create pool with virtual initial liquidity
    CreatePool {
        token_0: ApplicationId,
        // None means add pair to native token
        token_1: Option<ApplicationId>,
        amount_0_initial: Amount,
        amount_1_initial: Amount,
        amount_0_virtual: Amount,
        amount_1_virtual: Amount,
        block_timestamp: Timestamp,
    },
    SetFeeTo {
        account: Account,
    },
    SetFeeToSetter {
        account: Account,
    },
}

#[derive(Clone, Copy, Debug, Deserialize, Serialize)]
pub struct PoolParameters {
    pub token_0: ApplicationId,
    pub token_1: Option<ApplicationId>,
    pub router_application_id: ApplicationId,
}

scalar!(PoolParameters);

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize, InputObject)]
pub struct InstantiationArgument {
    pub amount_0: Amount,
    pub amount_1: Amount,
}

#[derive(Debug, Clone, Deserialize, Eq, PartialEq, Serialize, SimpleObject)]
pub struct Pool {
    pub token_0: ApplicationId,
    // None means add pair to native token
    pub token_1: Option<ApplicationId>,
    pub virtual_initial_liquidity: bool,
    pub amount_0_initial: Amount,
    pub amount_1_initial: Amount,
    pub reserve_0: Amount,
    pub reserve_1: Amount,
    pub pool_fee_percent: u16,
    pub protocol_fee_percent: u16,
    pub erc20: Meme,
    pub fee_to: Account,
    pub fee_to_setter: Account,
    pub price_0_cumulative: BigAmount,
    pub price_1_cumulative: BigAmount,
    pub k_last: Amount,
    pub block_timestamp: Timestamp,
}
