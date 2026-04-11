use crate::interfaces::state::StateInterface;
use abi::ams::{AmsMessage, AmsResponse, Metadata};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::{Account, ApplicationId};
use runtime::interfaces::{access_control::AccessControl, contract::ContractRuntimeContext};
use std::{cell::RefCell, rc::Rc};

pub struct UpdateHandler<R: ContractRuntimeContext + AccessControl, S: StateInterface> {
    _runtime: Rc<RefCell<R>>,
    state: S,

    owner: Account,
    application_id: ApplicationId,
    metadata: Metadata,
}

impl<R: ContractRuntimeContext + AccessControl, S: StateInterface> UpdateHandler<R, S> {
    pub fn new(runtime: Rc<RefCell<R>>, state: S, msg: &AmsMessage) -> Self {
        let AmsMessage::Update {
            owner,
            application_id,
            metadata,
        } = msg
        else {
            panic!("Invalid message");
        };

        Self {
            state,
            _runtime: runtime,

            owner: *owner,
            application_id: *application_id,
            metadata: metadata.clone(),
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl, S: StateInterface> Handler<AmsMessage, AmsResponse>
    for UpdateHandler<R, S>
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<AmsMessage, AmsResponse>>, HandlerError> {
        self.state
            .update_application(self.owner, self.application_id, self.metadata.clone())
            .await
            .map_err(|err| HandlerError::ProcessError(Box::new(err)))?;

        Ok(None)
    }
}
