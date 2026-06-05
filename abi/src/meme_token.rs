use linera_sdk::linera_base_types::ApplicationId;
use serde::{Deserialize, Serialize};

#[derive(Clone, Copy, Debug, Deserialize, Serialize, Eq, Hash, Ord, PartialEq, PartialOrd)]
pub enum MemeToken {
    Native,
    Fungible(ApplicationId),
}

impl From<ApplicationId> for MemeToken {
    fn from(application_id: ApplicationId) -> Self {
        Self::Fungible(application_id)
    }
}

impl From<Option<ApplicationId>> for MemeToken {
    fn from(application_id: Option<ApplicationId>) -> Self {
        match application_id {
            Some(application_id) => Self::Fungible(application_id),
            None => Self::Native,
        }
    }
}
