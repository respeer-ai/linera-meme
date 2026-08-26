use crate::interfaces::state::StateInterface;
use abi::proxy::state_v1::{ProxyStateV1Operation, ProxyStateV1Response};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use runtime::interfaces::{access_control::AccessControl, contract::ContractRuntimeContext};
use std::{cell::RefCell, rc::Rc};

pub struct MemeBytecodeIdHandler<R: ContractRuntimeContext + AccessControl, S: StateInterface> {
    _runtime: Rc<RefCell<R>>,
    state: S,
}

impl<R: ContractRuntimeContext + AccessControl, S: StateInterface> MemeBytecodeIdHandler<R, S> {
    pub fn new(runtime: Rc<RefCell<R>>, state: S, _op: &ProxyStateV1Operation) -> Self {
        Self {
            _runtime: runtime,
            state,
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl, S: StateInterface>
    Handler<(), ProxyStateV1Response> for MemeBytecodeIdHandler<R, S>
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<(), ProxyStateV1Response>>, HandlerError> {
        let mut outcome = HandlerOutcome::new();
        outcome.with_response(ProxyStateV1Response::ModuleId(self.state.meme_bytecode_id()));
        Ok(Some(outcome))
    }
}

pub struct MemeStateBytecodeIdsHandler<
    R: ContractRuntimeContext + AccessControl,
    S: StateInterface,
> {
    _runtime: Rc<RefCell<R>>,
    state: S,
}

impl<R: ContractRuntimeContext + AccessControl, S: StateInterface>
    MemeStateBytecodeIdsHandler<R, S>
{
    pub fn new(runtime: Rc<RefCell<R>>, state: S, _op: &ProxyStateV1Operation) -> Self {
        Self {
            _runtime: runtime,
            state,
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl, S: StateInterface>
    Handler<(), ProxyStateV1Response> for MemeStateBytecodeIdsHandler<R, S>
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<(), ProxyStateV1Response>>, HandlerError> {
        let ids = self
            .state
            .meme_state_bytecode_ids()
            .await
            .map_err(|error| HandlerError::ProcessError(Box::new(error)))?;
        let mut outcome = HandlerOutcome::new();
        outcome.with_response(ProxyStateV1Response::ModuleIds(ids));
        Ok(Some(outcome))
    }
}

pub struct SwapApplicationIdHandler<
    R: ContractRuntimeContext + AccessControl,
    S: StateInterface,
> {
    _runtime: Rc<RefCell<R>>,
    state: S,
}

impl<R: ContractRuntimeContext + AccessControl, S: StateInterface> SwapApplicationIdHandler<R, S> {
    pub fn new(runtime: Rc<RefCell<R>>, state: S, _op: &ProxyStateV1Operation) -> Self {
        Self {
            _runtime: runtime,
            state,
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl, S: StateInterface>
    Handler<(), ProxyStateV1Response> for SwapApplicationIdHandler<R, S>
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<(), ProxyStateV1Response>>, HandlerError> {
        let mut outcome = HandlerOutcome::new();
        outcome.with_response(ProxyStateV1Response::ApplicationId(
            self.state.swap_application_id(),
        ));
        Ok(Some(outcome))
    }
}
