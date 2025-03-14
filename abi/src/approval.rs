use linera_sdk::linera_base_types::Account;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Deserialize, Serialize, Default, Clone)]
pub struct Approval {
    approvers: HashMap<Account, bool>,
    least_approvals: usize,
}

impl Approval {
    pub fn new(least_approvals: usize) -> Self {
        Approval {
            approvers: HashMap::new(),
            least_approvals,
        }
    }

    pub fn approved(&self) -> bool {
        self.approvers
            .values()
            .filter(|&&v| v)
            .collect::<Vec<_>>()
            .len()
            >= self.least_approvals
    }

    pub fn voted(&self, owner: Account) -> bool {
        self.approvers.contains_key(&owner)
    }

    pub fn approve(&mut self, owner: Account) {
        assert!(!self.voted(owner), "Already voted");
        self.approvers.insert(owner, true);
    }

    pub fn reject(&mut self, owner: Account) {
        assert!(!self.voted(owner), "Already voted");
        self.approvers.insert(owner, false);
    }
}
