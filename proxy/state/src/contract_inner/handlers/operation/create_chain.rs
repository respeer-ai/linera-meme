use crate::interfaces::state::StateInterface;
use abi::proxy::state_v1::{ProxyStateV1Operation, ProxyStateV1Response};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::ChainId;
use runtime::interfaces::{access_control::AccessControl, contract::ContractRuntimeContext};
use std::{cell::RefCell, rc::Rc};

pub struct CreateChainHandler<R: ContractRuntimeContext + AccessControl, S: StateInterface> {
    runtime: Rc<RefCell<R>>,
    state: S,
    chain_id: ChainId,
}

impl<R: ContractRuntimeContext + AccessControl, S: StateInterface> CreateChainHandler<R, S> {
    pub fn new(runtime: Rc<RefCell<R>>, state: S, op: &ProxyStateV1Operation) -> Self {
        let ProxyStateV1Operation::CreateChain { chain_id, .. } = op else {
            panic!("Invalid operation");
        };
        Self {
            runtime,
            state,
            chain_id: *chain_id,
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl, S: StateInterface> Handler<(), ProxyStateV1Response>
    for CreateChainHandler<R, S>
{
    async fn handle(&mut self) -> Result<Option<HandlerOutcome<(), ProxyStateV1Response>>, HandlerError> {
        let created_at = self.runtime.borrow_mut().system_time();
        self.state
            .create_chain(self.chain_id, created_at)
            .map_err(|error| HandlerError::ProcessError(Box::new(error)))?;
        Ok(None)
    }
}
