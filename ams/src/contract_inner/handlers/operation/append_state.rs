use abi::{
    ams::abi::{AmsMessage, AmsOperation, AmsResponse},
    application_state_base::PublicStateBaseInterface,
};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::ApplicationId;
use runtime::interfaces::{access_control::AccessControl, contract::ContractRuntimeContext};
use std::{cell::RefCell, rc::Rc};

pub struct AppendStateHandler<
    R: ContractRuntimeContext + AccessControl,
    S: PublicStateBaseInterface,
> {
    runtime: Rc<RefCell<R>>,
    state: S,
    state_application_id: ApplicationId,
}

impl<R: ContractRuntimeContext + AccessControl, S: PublicStateBaseInterface>
    AppendStateHandler<R, S>
{
    pub fn new(runtime: Rc<RefCell<R>>, state: S, op: &AmsOperation) -> Self {
        let AmsOperation::AppendState {
            state_application_id,
        } = op
        else {
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
impl<R: ContractRuntimeContext + AccessControl, S: PublicStateBaseInterface>
    Handler<AmsMessage, AmsResponse> for AppendStateHandler<R, S>
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<AmsMessage, AmsResponse>>, HandlerError> {
        self.runtime
            .borrow_mut()
            .only_application_creator()
            .map_err(|error| HandlerError::RuntimeError(error.into()))?;

        self.state
            .append_state(self.state_application_id)
            .await
            .map_err(|error| HandlerError::ProcessError(error.into()))?;

        let mut outcome = HandlerOutcome::new();
        outcome.with_response(AmsResponse::Ok);
        Ok(Some(outcome))
    }
}
