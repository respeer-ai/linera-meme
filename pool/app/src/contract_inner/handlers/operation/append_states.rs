use abi::{
    application_state_base::PublicStateBaseInterface,
    pool::{PoolMessage, PoolOperation, PoolResponse},
};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::ApplicationId;
use runtime::interfaces::{access_control::AccessControl, contract::ContractRuntimeContext};
use std::{cell::RefCell, rc::Rc};

pub struct AppendStatesHandler<R: ContractRuntimeContext + AccessControl, S: PublicStateBaseInterface>
{
    runtime: Rc<RefCell<R>>,
    state: S,
    state_application_ids: Vec<ApplicationId>,
}

impl<R: ContractRuntimeContext + AccessControl, S: PublicStateBaseInterface>
    AppendStatesHandler<R, S>
{
    pub fn new(runtime: Rc<RefCell<R>>, state: S, op: &PoolOperation) -> Self {
        let PoolOperation::AppendStates {
            state_application_ids,
        } = op
        else {
            panic!("Invalid operation");
        };
        Self {
            runtime,
            state,
            state_application_ids: state_application_ids.clone(),
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl, S: PublicStateBaseInterface>
    Handler<PoolMessage, PoolResponse> for AppendStatesHandler<R, S>
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<PoolMessage, PoolResponse>>, HandlerError> {
        self.runtime
            .borrow_mut()
            .only_application_creator()
            .map_err(|error| HandlerError::RuntimeError(error.into()))?;

        for state_application_id in &self.state_application_ids {
            self.state
                .append_state(*state_application_id)
                .await
                .map_err(|error| HandlerError::ProcessError(error.into()))?;
        }

        let mut outcome = HandlerOutcome::new();
        outcome.with_response(PoolResponse::Ok);
        Ok(Some(outcome))
    }
}
