use async_graphql::Enum;
use serde::{Deserialize, Deserializer, Serialize};

#[derive(Default, Debug, Serialize, Clone, Eq, PartialEq, Enum, Copy)]
pub enum StoreType {
    #[default]
    Blob,
    Ipfs,
    S3,
}

impl<'de> Deserialize<'de> for StoreType {
    fn deserialize<D>(de: D) -> Result<Self, D::Error>
    where
        D: Deserializer<'de>,
    {
        let variant = String::deserialize(de)?;
        Ok(match variant.as_str() {
            "Blob" => StoreType::Blob,
            "Ipfs" => StoreType::Ipfs,
            "S3" => StoreType::S3,
            _ => todo!(),
        })
    }
}
