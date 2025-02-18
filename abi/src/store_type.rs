use async_graphql::Enum;
use serde::{Deserialize, Serialize};

#[derive(Default, Debug, Deserialize, Serialize, Clone, Eq, PartialEq, Enum, Copy)]
pub enum StoreType {
    #[default]
    Blob,
    Ipfs,
    S3,
}
