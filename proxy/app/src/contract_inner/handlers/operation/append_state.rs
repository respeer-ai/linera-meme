use abi::{
    application_state_base::PublicStateBaseInterface,
    proxy::{ProxyOperation, ProxyResponse},
};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::ApplicationId;
use runtime::interfaces::{
    access_control::AccessControl, contract::ContractRuntimeContext, meme::MemeRuntimeContext,
};
use std::{cell::RefCell, rc::Rc};

pub struct AppendStateHandler<
    R: ContractRuntimeContext + AccessControl + MemeRuntimeContext,
    S: PublicStateBaseInterface,
> {
    runtime: Rc<RefCell<R>>,
    state: S,
    state_application_id: ApplicationId,
}

impl<R: ContractRuntimeContext + AccessControl + MemeRuntimeContext, S: PublicStateBaseInterface>
    AppendStateHandler<R, S>
{
    pub fn new(runtime: Rc<RefCell<R>>, state: S, op: &ProxyOperation) -> Self {
        let ProxyOperation::AppendState { state_application_id } = op else {
            panic!("Invalid operation");
        };
        Self {
            runtime,
            state,
            state_application_id: *state_application_id,
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl + MemeRuntimeContext, S: PublicStateBaseInterface>
    Handler<abi::proxy::ProxyMessage, ProxyResponse> for AppendStateHandler<R, S>
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<abi::proxy::ProxyMessage, ProxyResponse>>, HandlerError> {
        self.runtime
            .borrow_mut()
            .only_application_creator()
            .map_err(|error| HandlerError::RuntimeError(error.into()))?;

        self.state
            .append_state(self.state_application_id)
            .await
            .map_err(|error| HandlerError::ProcessError(Box::new(error)))?;

        let mut outcome = HandlerOutcome::new();
        outcome.with_response(ProxyResponse::Ok);
        Ok(Some(outcome))
    }
}
