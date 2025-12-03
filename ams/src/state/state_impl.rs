use crate::instantiation_argument::InstantiationArgument;
use crate::interfaces::state::StateInterface;
use crate::state::{errors::StateError, AmsState};
use async_trait::async_trait;
use linera_sdk::linera_base_types::{AccountOwner, Amount, Timestamp};

#[async_trait(?Send)]
impl StateInterface for AmsState {
    type Error = StateError;

    fn instantiate(&mut self, argument: InstantiationArgument) {
        self._top_k.set(argument.top_k);
    }

    fn instantiation_argument(&self) -> InstantiationArgument {
        InstantiationArgument {
            top_k: *self._top_k.get(),
        }
    }

    fn top_k(&self) -> u8 {
        *self._top_k.get()
    }

    async fn value(&self, owner: AccountOwner) -> AmsItemValue {
        self._values
            .get(&owner)
            .await
            .unwrap_or(Some(AmsItemValue::default()))
            .unwrap_or(AmsItemValue::default())
    }

    fn update_value(
        &mut self,
        owner: AccountOwner,
        value: Amount,
        timestamp: Timestamp,
    ) -> Result<(), StateError> {
        self._values
            .insert(&owner, AmsItemValue { value, timestamp })?;

        // TODO: also insert to top_owners
        Ok(())
    }
}
