use linera_sdk::linera_base_types::Account;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Deserialize, Serialize, Default, Clone)]
pub struct Approval {
    pub approvers: HashMap<Account, bool>,
    pub least_approvals: usize,
}
