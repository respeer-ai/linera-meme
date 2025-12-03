use crate::{
    contract_inner::handlers::{errors::HandlerError, interfaces::Handler, types::HandlerOutcome},
    interfaces::state::StateInterface,
};
use abi::ams::Metadata;
use async_trait::async_trait;
use runtime::interfaces::{access_control::AccessControl, contract::ContractRuntimeContext};

pub struct RegisterHandler<R: ContractRuntimeContext + AccessControl, S: StateInterface> {
    runtime: R,
    state: S,

    metadata: Metadata,
}

impl<R: ContractRuntimeContext + AccessControl, S: StateInterface> RegisterHandler<R, S> {
    pub fn new(runtime: R, state: S, metadata: &Metadata) -> Self {
        Self {
            state,
            runtime,

            metadata: metadata.clone(),
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl, S: StateInterface> Handler
    for RegisterHandler<R, S>
{
    async fn handle(&mut self) -> Result<HandlerOutcome, HandlerError> {
        self.state
            .register_application(self.metadata.clone())
            .map_err(|e| HandlerError::RuntimeError(Box::new(e)))?;

        Ok(HandlerOutcome {
            messages: Vec::new(),
        })
    }
}
