use crate::interfaces::state::StateInterface;
use abi::{application_state_base::PublicStateBaseInterface, meme::MemeOperation};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::ApplicationId;
use runtime::interfaces::{access_control::AccessControl, contract::ContractRuntimeContext};
use std::{cell::RefCell, rc::Rc};

pub struct AppendStatesHandler<
    R: ContractRuntimeContext + AccessControl,
    S: StateInterface + PublicStateBaseInterface,
> {
    runtime: Rc<RefCell<R>>,
    state: S,
    state_application_ids: Vec<ApplicationId>,
}

impl<R: ContractRuntimeContext + AccessControl, S: StateInterface + PublicStateBaseInterface>
    AppendStatesHandler<R, S>
{
    pub fn new(runtime: Rc<RefCell<R>>, state: S, operation: &MemeOperation) -> Self {
        let MemeOperation::AppendStates {
            state_application_ids,
        } = operation
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
impl<R: ContractRuntimeContext + AccessControl, S: StateInterface + PublicStateBaseInterface>
    Handler<abi::meme::MemeMessage, abi::meme::MemeResponse> for AppendStatesHandler<R, S>
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<abi::meme::MemeMessage, abi::meme::MemeResponse>>, HandlerError>
    {
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
        outcome.with_response(abi::meme::MemeResponse::Ok);
        Ok(Some(outcome))
    }
}
