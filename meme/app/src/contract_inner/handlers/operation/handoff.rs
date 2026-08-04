use crate::interfaces::state::StateInterface;
use abi::{application_state_base::PublicStateBaseInterface, meme::MemeOperation};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use runtime::interfaces::{access_control::AccessControl, contract::ContractRuntimeContext};
use std::{cell::RefCell, rc::Rc};

pub struct HandoffHandler<
    R: ContractRuntimeContext + AccessControl,
    S: StateInterface + PublicStateBaseInterface,
> {
    runtime: Rc<RefCell<R>>,
    state: S,
    argument: abi::meme::HandoffArgument,
}

impl<R: ContractRuntimeContext + AccessControl, S: StateInterface + PublicStateBaseInterface>
    HandoffHandler<R, S>
{
    pub fn new(runtime: Rc<RefCell<R>>, state: S, operation: &MemeOperation) -> Self {
        let MemeOperation::Handoff { argument } = operation else {
            panic!("Invalid operation");
        };

        Self {
            runtime,
            state,
            argument: argument.clone(),
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl, S: StateInterface + PublicStateBaseInterface>
    Handler<abi::meme::MemeMessage, abi::meme::MemeResponse> for HandoffHandler<R, S>
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<abi::meme::MemeMessage, abi::meme::MemeResponse>>, HandlerError>
    {
        self.runtime
            .borrow_mut()
            .only_application_creator()
            .map_err(|error| HandlerError::RuntimeError(error.into()))?;

        StateInterface::handoff(&mut self.state, self.argument.clone())
            .await
            .map_err(|error| HandlerError::ProcessError(error.into()))?;

        let mut outcome = HandlerOutcome::new();
        outcome.with_response(abi::meme::MemeResponse::Ok);
        Ok(Some(outcome))
    }
}
