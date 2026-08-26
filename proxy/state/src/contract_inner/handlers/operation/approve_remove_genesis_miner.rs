use crate::interfaces::state::StateInterface;
use abi::proxy::state_v1::{ProxyStateV1Operation, ProxyStateV1Response};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::Account;
use runtime::interfaces::{access_control::AccessControl, contract::ContractRuntimeContext};
use std::{cell::RefCell, rc::Rc};

pub struct ApproveRemoveGenesisMinerHandler<
    R: ContractRuntimeContext + AccessControl,
    S: StateInterface,
> {
    _runtime: Rc<RefCell<R>>,
    state: S,
    owner: Account,
    operator: Account,
}

impl<R: ContractRuntimeContext + AccessControl, S: StateInterface>
    ApproveRemoveGenesisMinerHandler<R, S>
{
    pub fn new(runtime: Rc<RefCell<R>>, state: S, op: &ProxyStateV1Operation) -> Self {
        let ProxyStateV1Operation::ApproveRemoveGenesisMiner { owner, operator } = op else {
            panic!("Invalid operation");
        };
        Self {
            _runtime: runtime,
            state,
            owner: *owner,
            operator: *operator,
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl, S: StateInterface> Handler<(), ProxyStateV1Response>
    for ApproveRemoveGenesisMinerHandler<R, S>
{
    async fn handle(&mut self) -> Result<Option<HandlerOutcome<(), ProxyStateV1Response>>, HandlerError> {
        self.state
            .validate_operator(self.operator)
            .await
            .map_err(|error| HandlerError::ProcessError(Box::new(error)))?;
        self.state
            .approve_remove_genesis_miner(self.owner, self.operator)
            .await
            .map_err(|error| HandlerError::ProcessError(Box::new(error)))?;
        Ok(None)
    }
}
