use crate::interfaces::state::StateInterface;
use abi::proxy::state_v1::{ProxyStateV1Operation, ProxyStateV1Response};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::Account;
use runtime::interfaces::{access_control::AccessControl, contract::ContractRuntimeContext};
use std::{cell::RefCell, rc::Rc};

pub struct BanOperatorHandler<R: ContractRuntimeContext + AccessControl, S: StateInterface> {
    _runtime: Rc<RefCell<R>>,
    state: S,
    owner: Account,
}

impl<R: ContractRuntimeContext + AccessControl, S: StateInterface> BanOperatorHandler<R, S> {
    pub fn new(runtime: Rc<RefCell<R>>, state: S, op: &ProxyStateV1Operation) -> Self {
        let ProxyStateV1Operation::BanOperator { owner } = op else {
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
impl<R: ContractRuntimeContext + AccessControl, S: StateInterface> Handler<(), ProxyStateV1Response>
    for BanOperatorHandler<R, S>
{
    async fn handle(&mut self) -> Result<Option<HandlerOutcome<(), ProxyStateV1Response>>, HandlerError> {
        self.state
            .ban_operator(self.owner)
            .await
            .map_err(|error| HandlerError::ProcessError(Box::new(error)))?;
        Ok(None)
    }
}
