use crate::interfaces::state::StateInterface;
use abi::proxy::state_v1::{ProxyStateV1Operation, ProxyStateV1Response};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::{ApplicationId, ChainId, Timestamp};
use runtime::interfaces::{access_control::AccessControl, contract::ContractRuntimeContext};
use std::{cell::RefCell, rc::Rc};

pub struct ChainHandler<R: ContractRuntimeContext + AccessControl, S: StateInterface> {
    _runtime: Rc<RefCell<R>>,
    state: S,
    chain_id: ChainId,
}

impl<R: ContractRuntimeContext + AccessControl, S: StateInterface> ChainHandler<R, S> {
    pub fn new(runtime: Rc<RefCell<R>>, state: S, op: &ProxyStateV1Operation) -> Self {
        let ProxyStateV1Operation::Chain { chain_id } = op else {
            panic!("Invalid operation");
        };
        Self {
            _runtime: runtime,
            state,
            chain_id: *chain_id,
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl, S: StateInterface>
    Handler<(), ProxyStateV1Response> for ChainHandler<R, S>
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<(), ProxyStateV1Response>>, HandlerError> {
        let chain = self
            .state
            .chain(self.chain_id)
            .await
            .map_err(|error| HandlerError::ProcessError(Box::new(error)))?;
        let mut outcome = HandlerOutcome::new();
        outcome.with_response(ProxyStateV1Response::Chain(chain));
        Ok(Some(outcome))
    }
}

pub struct ChainsHandler<R: ContractRuntimeContext + AccessControl, S: StateInterface> {
    _runtime: Rc<RefCell<R>>,
    state: S,
    created_after: Option<Timestamp>,
}

impl<R: ContractRuntimeContext + AccessControl, S: StateInterface> ChainsHandler<R, S> {
    pub fn new(runtime: Rc<RefCell<R>>, state: S, op: &ProxyStateV1Operation) -> Self {
        let ProxyStateV1Operation::Chains { created_after } = op else {
            panic!("Invalid operation");
        };
        Self {
            _runtime: runtime,
            state,
            created_after: *created_after,
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl, S: StateInterface>
    Handler<(), ProxyStateV1Response> for ChainsHandler<R, S>
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<(), ProxyStateV1Response>>, HandlerError> {
        let chains = self
            .state
            .chains(self.created_after)
            .await
            .map_err(|error| HandlerError::ProcessError(Box::new(error)))?;
        let mut outcome = HandlerOutcome::new();
        outcome.with_response(ProxyStateV1Response::Chains(chains));
        Ok(Some(outcome))
    }
}

pub struct ChainByTokenHandler<R: ContractRuntimeContext + AccessControl, S: StateInterface> {
    _runtime: Rc<RefCell<R>>,
    state: S,
    token: ApplicationId,
}

impl<R: ContractRuntimeContext + AccessControl, S: StateInterface> ChainByTokenHandler<R, S> {
    pub fn new(runtime: Rc<RefCell<R>>, state: S, op: &ProxyStateV1Operation) -> Self {
        let ProxyStateV1Operation::ChainByToken { token } = op else {
            panic!("Invalid operation");
        };
        Self {
            _runtime: runtime,
            state,
            token: *token,
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl, S: StateInterface>
    Handler<(), ProxyStateV1Response> for ChainByTokenHandler<R, S>
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<(), ProxyStateV1Response>>, HandlerError> {
        let chain = self
            .state
            .chain_by_token(self.token)
            .await
            .map_err(|error| HandlerError::ProcessError(Box::new(error)))?;
        let mut outcome = HandlerOutcome::new();
        outcome.with_response(ProxyStateV1Response::Chain(chain));
        Ok(Some(outcome))
    }
}
