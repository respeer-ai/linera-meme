use crate::instantiation_argument::InstantiationArgument;
use async_trait::async_trait;
use linera_sdk::linera_base_types::{AccountOwner, Amount, Timestamp};

#[async_trait(?Send)]
pub trait StateInterface {
    type Error: std::fmt::Debug + std::error::Error + 'static;
    type ValueType;

    fn instantiate(&mut self, argument: InstantiationArgument);
    fn instantiation_argument(&self) -> InstantiationArgument;
    fn top_k(&self) -> u8;
    async fn value(&self, owner: AccountOwner) -> Self::ValueType;
    fn update_value(
        &mut self,
        owner: AccountOwner,
        value: Amount,
        timestamp: Timestamp,
    ) -> Result<(), Self::Error>;
}
