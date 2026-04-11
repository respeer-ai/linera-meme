use crate::interfaces::state::StateInterface;
use abi::ams::{AmsMessage, AmsResponse};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::ApplicationId;
use runtime::interfaces::{access_control::AccessControl, contract::ContractRuntimeContext};
use std::{cell::RefCell, rc::Rc};

pub struct ClaimHandler<R: ContractRuntimeContext + AccessControl, S: StateInterface> {
    runtime: Rc<RefCell<R>>,
    state: S,

    application_id: ApplicationId,
}

impl<R: ContractRuntimeContext + AccessControl, S: StateInterface> ClaimHandler<R, S> {
    pub fn new(runtime: Rc<RefCell<R>>, state: S, msg: &AmsMessage) -> Self {
        let AmsMessage::Claim { application_id } = msg else {
            panic!("Invalid message");
        };

        Self {
            state,
            runtime,

            application_id: *application_id,
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl, S: StateInterface> Handler<AmsMessage, AmsResponse>
    for ClaimHandler<R, S>
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<AmsMessage, AmsResponse>>, HandlerError> {
        let owner = self.runtime.borrow_mut().message_signer_account();
        self.state
            .claim_application(owner, self.application_id)
            .await
            .map_err(|err| HandlerError::ProcessError(Box::new(err)))?;

        Ok(None)
    }
}
