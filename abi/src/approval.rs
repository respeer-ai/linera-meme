use linera_sdk::base::Account;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Deserialize, Serialize, Default, Clone)]
pub struct Approval {
    pub approvers: HashMap<Account, bool>,
    pub least_approvals: usize,
}
