use linera_sdk::{
    graphql::GraphQLMutationRoot,
    linera_base_types::{Account, Amount, ApplicationId, ContractAbi, ServiceAbi},
};
use serde::{Deserialize, Serialize};

use crate::pool::{Pool, Transaction};

#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
pub struct StateInstantiationArgument {
    pub business_application_id: ApplicationId,
    pub operator: Option<Account>,
}

pub struct PoolStateAbi;

impl ContractAbi for PoolStateAbi {
    type Operation = PoolStateV1Operation;
    type Response = PoolStateV1Response;
}

impl ServiceAbi for PoolStateAbi {
    type Query = async_graphql::Request;
    type QueryResponse = async_graphql::Response;
}

#[derive(Debug, Clone, Deserialize, Eq, PartialEq, Serialize, GraphQLMutationRoot)]
pub enum PoolStateV1Operation {
    SetOperator {
        new_operator: Account,
    },
    Handoff {
        new_business_application_id: ApplicationId,
    },

    Initialize {
        pool: Pool,
        router_application_id: ApplicationId,
    },
    SetPool {
        pool: Pool,
    },
    MintShares {
        to: Account,
        amount: Amount,
    },
    BurnShares {
        from: Account,
        amount: Amount,
    },
    CreditClaimable {
        token: Option<ApplicationId>,
        owner: Account,
        amount: Amount,
    },
    DebitClaimable {
        token: Option<ApplicationId>,
        owner: Account,
        amount: Amount,
    },
    Claim {
        token: Option<ApplicationId>,
        owner: Account,
        amount: Amount,
    },
    ClaimSuccess {
        token: Option<ApplicationId>,
        owner: Account,
        amount: Amount,
    },
    ClaimFail {
        token: Option<ApplicationId>,
        owner: Account,
        amount: Amount,
    },
    SetFeeTo {
        operator: Account,
        account: Account,
    },
    SetFeeToSetter {
        operator: Account,
        account: Account,
    },
    BuildTransaction {
        transaction: Transaction,
    },

    Pool,
    RouterApplicationId,
    TotalSupply,
    Liquidity {
        account: Account,
    },
    ClaimableBalance {
        token: Option<ApplicationId>,
        owner: Account,
    },
    ClaimingBalance {
        token: Option<ApplicationId>,
        owner: Account,
    },
}

#[derive(Debug, Clone, Deserialize, Eq, PartialEq, Serialize)]
pub enum PoolStateV1Response {
    Ok,
    Fail(String),
    Pool(Pool),
    RouterApplicationId(ApplicationId),
    TotalSupply(Amount),
    Liquidity(Amount),
    ClaimableBalance(Amount),
    ClaimingBalance(Amount),
    Transaction(Transaction),
}
