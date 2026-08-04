use async_graphql::{InputObject, Request, Response};
use linera_sdk::{
    graphql::GraphQLMutationRoot,
    linera_base_types::{Account, Amount, ApplicationId, ContractAbi, ServiceAbi, Timestamp},
};
use serde::{Deserialize, Serialize};

use super::abi::{Meme, MiningInfo};

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
pub struct StateInstantiationArgument {
    pub business_application_id: ApplicationId,
    pub operator: Option<Account>,
    pub proxy_application_id: Option<ApplicationId>,
}

pub struct MemeStateAbi;

impl ContractAbi for MemeStateAbi {
    type Operation = MemeStateV1Operation;
    type Response = MemeStateV1Response;
}

impl ServiceAbi for MemeStateAbi {
    type Query = Request;
    type QueryResponse = Response;
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize, InputObject)]
pub struct InitializeArgument {
    pub owner: Account,
    pub holder: Account,
    pub meme: Meme,
    pub initial_owner_balance: Amount,
    pub blob_gateway_application_id: Option<ApplicationId>,
    pub ams_application_id: Option<ApplicationId>,
    pub swap_application_id: Option<ApplicationId>,
    pub enable_mining: bool,
    pub mining_supply: Option<Amount>,
    pub now: Timestamp,
}

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize, InputObject)]
pub struct HandoffArgument {
    pub new_business_application_id: ApplicationId,
    pub new_proxy_application_id: Option<ApplicationId>,
    pub new_swap_application_id: Option<ApplicationId>,
    pub new_ams_application_id: Option<ApplicationId>,
    pub new_blob_gateway_application_id: Option<ApplicationId>,
}

#[derive(Debug, Clone, Deserialize, Eq, PartialEq, Serialize, GraphQLMutationRoot)]
pub enum MemeStateV1Operation {
    Initialize { argument: InitializeArgument },
    Transfer {
        from: Account,
        to: Account,
        amount: Amount,
    },
    TransferFrom {
        origin: Account,
        from: Account,
        to: Account,
        amount: Amount,
    },
    TransferFromApplication {
        from: Account,
        to: Account,
        amount: Amount,
    },
    Approve {
        origin: Account,
        spender: Account,
        amount: Amount,
    },
    Mint {
        to: Account,
        amount: Amount,
    },
    TransferOwnership {
        owner: Account,
        new_owner: Account,
    },
    Redeem {
        from: Account,
        to: Account,
        amount: Option<Amount>,
    },
    MiningReward {
        owner: Account,
        reward_amount: Amount,
        mining_info: MiningInfo,
    },
    MiningInfo,
    Handoff {
        argument: HandoffArgument,
    },
    Balance {
        owner: Account,
    },
    Allowance {
        owner: Account,
        spender: Account,
    },
    Owner,
    SwapApplicationId,
    ProxyApplicationId,
    StartMining,
}

#[derive(Debug, Clone, Deserialize, Eq, PartialEq, Serialize)]
pub enum MemeStateV1Response {
    Ok,
    Fail(String),
    Balance(Amount),
    Allowance(Amount),
    Owner(Account),
    MiningInfo(MiningInfo),
    SwapApplicationId(Option<ApplicationId>),
    ProxyApplicationId(Option<ApplicationId>),
}
