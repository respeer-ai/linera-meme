use crate::interfaces::state::StateInterface;
use abi::proxy::state_v1::{ProxyStateV1Operation, ProxyStateV1Response};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use runtime::interfaces::{access_control::AccessControl, contract::ContractRuntimeContext};
use std::{cell::RefCell, rc::Rc};

pub struct RegisterMinerHandler<R: ContractRuntimeContext + AccessControl, S: StateInterface> {
    runtime: Rc<RefCell<R>>,
    state: S,
}

impl<R: ContractRuntimeContext + AccessControl, S: StateInterface> RegisterMinerHandler<R, S> {
    pub fn new(runtime: Rc<RefCell<R>>, state: S, _op: &ProxyStateV1Operation) -> Self {
        Self { runtime, state }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl, S: StateInterface> Handler<(), ProxyStateV1Response>
    for RegisterMinerHandler<R, S>
{
    async fn handle(&mut self) -> Result<Option<HandlerOutcome<(), ProxyStateV1Response>>, HandlerError> {
        let owner = self.runtime.borrow_mut().authenticated_account();
        let now = self.runtime.borrow_mut().system_time();
        self.state
            .register_miner(owner, now)
            .await
            .map_err(|error| HandlerError::ProcessError(Box::new(error)))?;
        Ok(None)
    }
}
