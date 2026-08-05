use crate::interfaces::state::StateInterface;
use abi::proxy::{ProxyOperation, ProxyResponse};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::ModuleId;
use runtime::interfaces::{
    access_control::AccessControl, contract::ContractRuntimeContext, meme::MemeRuntimeContext,
};
use std::{cell::RefCell, rc::Rc};

pub struct SetMemeBytecodeIdsHandler<
    R: ContractRuntimeContext + AccessControl + MemeRuntimeContext,
    S: StateInterface,
> {
    runtime: Rc<RefCell<R>>,
    state: S,

    business_bytecode_id: ModuleId,
    state_bytecode_id: ModuleId,
}

impl<R: ContractRuntimeContext + AccessControl + MemeRuntimeContext, S: StateInterface>
    SetMemeBytecodeIdsHandler<R, S>
{
    pub fn new(runtime: Rc<RefCell<R>>, state: S, op: &ProxyOperation) -> Self {
        let ProxyOperation::SetMemeBytecodeIds {
            business_bytecode_id,
            state_bytecode_id,
        } = op
        else {
            panic!("Invalid operation");
        };

        Self {
            runtime,
            state,
            business_bytecode_id: *business_bytecode_id,
            state_bytecode_id: *state_bytecode_id,
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl + MemeRuntimeContext, S: StateInterface>
    Handler<abi::proxy::ProxyMessage, ProxyResponse> for SetMemeBytecodeIdsHandler<R, S>
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<abi::proxy::ProxyMessage, ProxyResponse>>, HandlerError> {
        self.runtime
            .borrow_mut()
            .only_application_creator()
            .map_err(|error| HandlerError::RuntimeError(error.into()))?;

        let operator = self.runtime.borrow_mut().authenticated_account();
        self.state
            .validate_operator(operator)
            .await
            .map_err(|error| HandlerError::ProcessError(Box::new(error)))?;

        self.state
            .set_meme_bytecode_ids(self.business_bytecode_id, self.state_bytecode_id)
            .await
            .map_err(|error| HandlerError::ProcessError(Box::new(error)))?;

        let mut outcome = HandlerOutcome::new();
        outcome.with_response(ProxyResponse::Ok);
        Ok(Some(outcome))
    }
}
