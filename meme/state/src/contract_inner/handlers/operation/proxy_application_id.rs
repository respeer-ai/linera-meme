use abi::meme::{MemeStateV1Operation, MemeStateV1Response};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use runtime::interfaces::contract::ContractRuntimeContext;
use std::{cell::RefCell, rc::Rc};

use crate::interfaces::state::StateInterface;

pub struct ProxyApplicationIdHandler<R: ContractRuntimeContext, S: StateInterface> {
    state: S,
    _runtime: Rc<RefCell<R>>,
}

impl<R: ContractRuntimeContext, S: StateInterface> ProxyApplicationIdHandler<R, S> {
    pub fn new(runtime: Rc<RefCell<R>>, state: S, _operation: &MemeStateV1Operation) -> Self {
        Self {
            state,
            _runtime: runtime,
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext, S: StateInterface> Handler<(), MemeStateV1Response>
    for ProxyApplicationIdHandler<R, S>
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<(), MemeStateV1Response>>, HandlerError> {
        let proxy_application_id = self
            .state
            .proxy_application_id()
            .await
            .map_err(|error| HandlerError::ProcessError(error.into()))?;

        let mut outcome = HandlerOutcome::new();
        outcome.with_response(MemeStateV1Response::ProxyApplicationId(proxy_application_id));
        Ok(Some(outcome))
    }
}
