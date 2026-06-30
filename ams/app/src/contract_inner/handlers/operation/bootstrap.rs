use abi::{
    ams::abi::{AmsMessage, AmsOperation, AmsResponse},
    application_state_base::PublicStateBaseInterface,
};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use runtime::interfaces::{access_control::AccessControl, contract::ContractRuntimeContext};
use std::{cell::RefCell, rc::Rc};

pub struct BootstrapHandler<
    R: ContractRuntimeContext + AccessControl,
    S: PublicStateBaseInterface<BootstrapArgument = ()>,
> {
    runtime: Rc<RefCell<R>>,
    state: S,
}

impl<R, S> BootstrapHandler<R, S>
where
    R: ContractRuntimeContext + AccessControl,
    S: PublicStateBaseInterface<BootstrapArgument = ()>,
{
    pub fn new(runtime: Rc<RefCell<R>>, state: S, op: &AmsOperation) -> Self {
        let AmsOperation::Bootstrap = op else {
            panic!("Invalid operation");
        };
        Self { runtime, state }
    }
}

#[async_trait(?Send)]
impl<R, S> Handler<AmsMessage, AmsResponse> for BootstrapHandler<R, S>
where
    R: ContractRuntimeContext + AccessControl,
    S: PublicStateBaseInterface<BootstrapArgument = ()>,
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<AmsMessage, AmsResponse>>, HandlerError> {
        self.runtime
            .borrow_mut()
            .only_application_creator()
            .map_err(|error| HandlerError::RuntimeError(error.into()))?;
        self.state
            .bootstrap(())
            .await
            .map_err(|error| HandlerError::ProcessError(error.into()))?;

        let mut outcome = HandlerOutcome::new();
        outcome.with_response(AmsResponse::Ok);
        Ok(Some(outcome))
    }
}
