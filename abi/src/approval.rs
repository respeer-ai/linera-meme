use linera_sdk::base::Owner;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Deserialize, Serialize, Default, Clone)]
pub struct Approval {
    pub approvers: HashMap<Owner, bool>,
    pub least_approvals: usize,
}
