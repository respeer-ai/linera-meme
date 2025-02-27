use async_graphql::InputObject;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Deserialize, Serialize, Eq, PartialEq, InputObject)]
pub struct Transaction {
    pub empty: u32,
}
