use abi::meme::{MemeStateV1Operation, MemeStateV1Response};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use runtime::interfaces::{access_control::AccessControl, contract::ContractRuntimeContext};
use std::{cell::RefCell, rc::Rc};

use crate::interfaces::state::StateInterface;

pub struct MiningInfoHandler<S: StateInterface> {
    state: S,
}

impl<S: StateInterface> MiningInfoHandler<S> {
    pub fn new<R: ContractRuntimeContext + AccessControl>(
        _runtime: Rc<RefCell<R>>,
        state: S,
        operation: &MemeStateV1Operation,
    ) -> Self {
        let MemeStateV1Operation::MiningInfo = operation else {
            panic!("Invalid operation");
        };

        Self { state }
    }
}

#[async_trait(?Send)]
impl<S: StateInterface> Handler<(), MemeStateV1Response> for MiningInfoHandler<S> {
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<(), MemeStateV1Response>>, HandlerError> {
        let mining_info = self
            .state
            .mining_info()
            .await
            .map_err(|error| HandlerError::ProcessError(error.into()))?;

        let mut outcome = HandlerOutcome::new();
        outcome.with_response(MemeStateV1Response::MiningInfo(mining_info));
        Ok(Some(outcome))
    }
}
