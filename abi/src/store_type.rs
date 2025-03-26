use async_graphql::scalar;
use serde::{Deserialize, Serialize};

#[derive(Default, Debug, Deserialize, Serialize, Clone, Eq, PartialEq, Copy)]
pub enum StoreType {
    #[default]
    Blob,
    Ipfs,
    S3,
}

scalar!(StoreType);
