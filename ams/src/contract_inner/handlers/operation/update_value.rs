use crate::{
    contract_inner::handlers::{errors::HandlerError, interfaces::Handler, types::HandlerOutcome},
    interfaces::{
        access_control::AccessControl, runtime::contract::ContractRuntimeContext,
        state::StateInterface,
    },
};
use async_trait::async_trait;

use linera_sdk::linera_base_types::{AccountOwner, Amount};

pub struct UpdateValueHandler<R: ContractRuntimeContext + AccessControl, S: StateInterface> {
    runtime: R,
    state: S,

    owner: AccountOwner,
    value: Amount,
}

impl<R: ContractRuntimeContext + AccessControl, S: StateInterface> UpdateValueHandler<R, S> {
    pub fn new(runtime: R, state: S, owner: &AccountOwner, value: &Amount) -> Self {
        Self {
            state,
            runtime,

            owner: *owner,
            value: *value,
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl, S: StateInterface> Handler
    for UpdateValueHandler<R, S>
{
    async fn handle(&mut self) -> Result<HandlerOutcome, HandlerError> {
        self.runtime
            .only_application_creator()
            .map_err(|e| HandlerError::RuntimeError(Box::new(e)))?;

        let now = self.runtime.system_time();
        self.state
            .update_value(self.owner, self.value, now)
            .map_err(|e| HandlerError::RuntimeError(Box::new(e)))?;

        Ok(HandlerOutcome {
            messages: Vec::new(),
        })
    }
}
