use crate::interfaces::state::StateInterface;
use abi::proxy::state_v1::{ProxyStateV1Operation, ProxyStateV1Response};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::Account;
use runtime::interfaces::{access_control::AccessControl, contract::ContractRuntimeContext};
use std::{cell::RefCell, rc::Rc};

pub struct IsGenesisMinerHandler<R: ContractRuntimeContext + AccessControl, S: StateInterface> {
    _runtime: Rc<RefCell<R>>,
    state: S,
    owner: Account,
}

impl<R: ContractRuntimeContext + AccessControl, S: StateInterface> IsGenesisMinerHandler<R, S> {
    pub fn new(runtime: Rc<RefCell<R>>, state: S, op: &ProxyStateV1Operation) -> Self {
        let ProxyStateV1Operation::IsGenesisMiner { owner } = op else {
            panic!("Invalid operation");
        };
        Self {
            _runtime: runtime,
            state,
            owner: *owner,
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl, S: StateInterface>
    Handler<(), ProxyStateV1Response> for IsGenesisMinerHandler<R, S>
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<(), ProxyStateV1Response>>, HandlerError> {
        let value = self
            .state
            .is_genesis_miner(self.owner)
            .await
            .map_err(|error| HandlerError::ProcessError(Box::new(error)))?;
        let mut outcome = HandlerOutcome::new();
        outcome.with_response(ProxyStateV1Response::Bool(value));
        Ok(Some(outcome))
    }
}

pub struct MinersHandler<R: ContractRuntimeContext + AccessControl, S: StateInterface> {
    _runtime: Rc<RefCell<R>>,
    state: S,
}

impl<R: ContractRuntimeContext + AccessControl, S: StateInterface> MinersHandler<R, S> {
    pub fn new(runtime: Rc<RefCell<R>>, state: S, _op: &ProxyStateV1Operation) -> Self {
        Self {
            _runtime: runtime,
            state,
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl, S: StateInterface>
    Handler<(), ProxyStateV1Response> for MinersHandler<R, S>
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<(), ProxyStateV1Response>>, HandlerError> {
        let miners = self
            .state
            .miners()
            .await
            .map_err(|error| HandlerError::ProcessError(Box::new(error)))?;
        let mut outcome = HandlerOutcome::new();
        outcome.with_response(ProxyStateV1Response::Miners(miners));
        Ok(Some(outcome))
    }
}

pub struct MinerOwnersHandler<R: ContractRuntimeContext + AccessControl, S: StateInterface> {
    _runtime: Rc<RefCell<R>>,
    state: S,
}

impl<R: ContractRuntimeContext + AccessControl, S: StateInterface> MinerOwnersHandler<R, S> {
    pub fn new(runtime: Rc<RefCell<R>>, state: S, _op: &ProxyStateV1Operation) -> Self {
        Self {
            _runtime: runtime,
            state,
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl, S: StateInterface>
    Handler<(), ProxyStateV1Response> for MinerOwnersHandler<R, S>
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<(), ProxyStateV1Response>>, HandlerError> {
        let owners = self
            .state
            .miner_owners()
            .await
            .map_err(|error| HandlerError::ProcessError(Box::new(error)))?;
        let mut outcome = HandlerOutcome::new();
        outcome.with_response(ProxyStateV1Response::AccountOwners(owners));
        Ok(Some(outcome))
    }
}

pub struct GenesisMinersHandler<R: ContractRuntimeContext + AccessControl, S: StateInterface> {
    _runtime: Rc<RefCell<R>>,
    state: S,
}

impl<R: ContractRuntimeContext + AccessControl, S: StateInterface> GenesisMinersHandler<R, S> {
    pub fn new(runtime: Rc<RefCell<R>>, state: S, _op: &ProxyStateV1Operation) -> Self {
        Self {
            _runtime: runtime,
            state,
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl, S: StateInterface>
    Handler<(), ProxyStateV1Response> for GenesisMinersHandler<R, S>
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<(), ProxyStateV1Response>>, HandlerError> {
        let miners = self
            .state
            .genesis_miners()
            .await
            .map_err(|error| HandlerError::ProcessError(Box::new(error)))?;
        let mut outcome = HandlerOutcome::new();
        outcome.with_response(ProxyStateV1Response::Miners(miners));
        Ok(Some(outcome))
    }
}
