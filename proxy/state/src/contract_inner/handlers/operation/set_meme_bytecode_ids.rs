use crate::interfaces::state::StateInterface;
use abi::proxy::state_v1::{ProxyStateV1Operation, ProxyStateV1Response};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::ModuleId;
use runtime::interfaces::{access_control::AccessControl, contract::ContractRuntimeContext};
use std::{cell::RefCell, rc::Rc};

pub struct SetMemeBytecodeIdsHandler<
    R: ContractRuntimeContext + AccessControl,
    S: StateInterface,
> {
    _runtime: Rc<RefCell<R>>,
    state: S,
    business_bytecode_id: ModuleId,
    state_bytecode_id: ModuleId,
}

impl<R: ContractRuntimeContext + AccessControl, S: StateInterface> SetMemeBytecodeIdsHandler<R, S> {
    pub fn new(runtime: Rc<RefCell<R>>, state: S, op: &ProxyStateV1Operation) -> Self {
        let ProxyStateV1Operation::SetMemeBytecodeIds {
            business_bytecode_id,
            state_bytecode_id,
        } = op
        else {
            panic!("Invalid operation");
        };
        Self {
            _runtime: runtime,
            state,
            business_bytecode_id: *business_bytecode_id,
            state_bytecode_id: *state_bytecode_id,
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl, S: StateInterface> Handler<(), ProxyStateV1Response>
    for SetMemeBytecodeIdsHandler<R, S>
{
    async fn handle(&mut self) -> Result<Option<HandlerOutcome<(), ProxyStateV1Response>>, HandlerError> {
        self.state
            .set_meme_bytecode_ids(self.business_bytecode_id, self.state_bytecode_id)
            .await
            .map_err(|error| HandlerError::ProcessError(Box::new(error)))?;
        Ok(None)
    }
}
