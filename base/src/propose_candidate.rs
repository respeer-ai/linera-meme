use async_graphql::{Enum, SimpleObject};
use linera_sdk::linera_base_types::AccountOwner;
use serde::{Deserialize, Serialize};

#[derive(Clone, Default, Deserialize, Serialize, Debug, Enum, Copy, Eq, PartialEq)]
pub enum CandidateState {
    #[default]
    Proposed,
    Approved,
    Rejected,
    Confirmed,
}

#[derive(Clone, Deserialize, Serialize, Debug, SimpleObject)]
pub struct Candidate {
    pub owner: AccountOwner,
    pub state: CandidateState,
}
