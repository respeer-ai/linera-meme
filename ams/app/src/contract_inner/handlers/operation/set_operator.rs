use abi::{
    ams::abi::{AmsMessage, AmsOperation, AmsResponse},
    application_state_base::PublicStateBaseInterface,
};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::Account;
use runtime::interfaces::{access_control::AccessControl, contract::ContractRuntimeContext};
use std::{cell::RefCell, rc::Rc};

pub struct SetOperatorHandler<
    R: ContractRuntimeContext + AccessControl,
    S: PublicStateBaseInterface,
> {
    runtime: Rc<RefCell<R>>,
    state: S,
    new_operator: Account,
}

impl<R: ContractRuntimeContext + AccessControl, S: PublicStateBaseInterface>
    SetOperatorHandler<R, S>
{
    pub fn new(runtime: Rc<RefCell<R>>, state: S, op: &AmsOperation) -> Self {
        let AmsOperation::SetOperator { new_operator } = op else {
            panic!("Invalid operation");
        };

        Self {
            runtime,
            state,
            new_operator: *new_operator,
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl, S: PublicStateBaseInterface>
    Handler<AmsMessage, AmsResponse> for SetOperatorHandler<R, S>
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<AmsMessage, AmsResponse>>, HandlerError> {
        self.runtime
            .borrow_mut()
            .only_application_creator()
            .map_err(|error| HandlerError::RuntimeError(error.into()))?;

        self.state
            .set_operator(self.new_operator)
            .await
            .map_err(|error| HandlerError::ProcessError(error.into()))?;

        let mut outcome = HandlerOutcome::new();
        outcome.with_response(AmsResponse::Ok);
        Ok(Some(outcome))
    }
}
