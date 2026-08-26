use crate::interfaces::state::StateInterface;
use abi::proxy::{state_v1::ProxyStateV1Operation, InitializeArgument, ProxyStateV1Response};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use runtime::interfaces::{access_control::AccessControl, contract::ContractRuntimeContext};
use std::{cell::RefCell, rc::Rc};

pub struct InitializeHandler<
    R: ContractRuntimeContext + AccessControl,
    S: StateInterface,
> {
    _runtime: Rc<RefCell<R>>,
    state: S,
    argument: InitializeArgument,
}

impl<R: ContractRuntimeContext + AccessControl, S: StateInterface> InitializeHandler<R, S> {
    pub fn new(runtime: Rc<RefCell<R>>, state: S, op: &ProxyStateV1Operation) -> Self {
        let ProxyStateV1Operation::Initialize { argument } = op else {
            panic!("Invalid operation");
        };
        Self {
            _runtime: runtime,
            state,
            argument: argument.clone(),
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl, S: StateInterface> Handler<(), ProxyStateV1Response>
    for InitializeHandler<R, S>
{
    async fn handle(&mut self) -> Result<Option<HandlerOutcome<(), ProxyStateV1Response>>, HandlerError> {
        self.state
            .initialize(self.argument.clone())
            .await
            .map_err(|error| HandlerError::ProcessError(Box::new(error)))?;
        Ok(None)
    }
}
