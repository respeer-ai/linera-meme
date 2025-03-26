use anyhow::anyhow;
use async_graphql::Enum;
use serde::{Deserialize, Serialize};
use std::str::FromStr;

#[derive(Default, Debug, Deserialize, Serialize, Clone, Eq, PartialEq, Enum, Copy)]
pub enum StoreType {
    #[default]
    Blob,
    Ipfs,
    S3,
}

impl FromStr for StoreType {
    type Err = anyhow::Error;

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        match s {
            "Blob" => Ok(Self::Blob),
            "Ipfs" => Ok(Self::Ipfs),
            "S3" => Ok(Self::S3),
            _ => Err(anyhow!("Invalid enum! Enum: {}", s)),
        }
    }
}
