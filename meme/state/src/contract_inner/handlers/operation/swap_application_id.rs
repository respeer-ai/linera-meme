use abi::meme::{MemeStateV1Operation, MemeStateV1Response};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use runtime::interfaces::contract::ContractRuntimeContext;
use std::{cell::RefCell, rc::Rc};

use crate::interfaces::state::StateInterface;

pub struct SwapApplicationIdHandler<
    R: ContractRuntimeContext,
    S: StateInterface,
> {
    state: S,
    _runtime: Rc<RefCell<R>>,
}

impl<R: ContractRuntimeContext, S: StateInterface> SwapApplicationIdHandler<R, S> {
    pub fn new(runtime: Rc<RefCell<R>>, state: S, _operation: &MemeStateV1Operation) -> Self {
        Self { state, _runtime: runtime }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext, S: StateInterface> Handler<(), MemeStateV1Response>
    for SwapApplicationIdHandler<R, S>
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<(), MemeStateV1Response>>, HandlerError> {
        let swap_application_id = self
            .state
            .swap_application_id()
            .await
            .map_err(|error| HandlerError::ProcessError(error.into()))?;

        let mut outcome = HandlerOutcome::new();
        outcome.with_response(MemeStateV1Response::SwapApplicationId(swap_application_id));
        Ok(Some(outcome))
    }
}
