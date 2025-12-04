use crate::interfaces::state::StateInterface;
use abi::ams::{AmsMessage, Metadata};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::{Account, ApplicationId};
use runtime::interfaces::{access_control::AccessControl, contract::ContractRuntimeContext};
use std::{cell::RefCell, rc::Rc};

pub struct UpdateHandler<R: ContractRuntimeContext + AccessControl, S: StateInterface> {
    _runtime: Rc<RefCell<R>>,
    _state: S,

    _owner: Account,
    _application_id: ApplicationId,
    _metadata: Metadata,
}

impl<R: ContractRuntimeContext + AccessControl, S: StateInterface> UpdateHandler<R, S> {
    pub fn new(
        runtime: Rc<RefCell<R>>,
        state: S,
        owner: Account,
        application_id: ApplicationId,
        metadata: &Metadata,
    ) -> Self {
        Self {
            _state: state,
            _runtime: runtime,

            _owner: owner,
            _application_id: application_id,
            _metadata: metadata.clone(),
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl, S: StateInterface> Handler<AmsMessage>
    for UpdateHandler<R, S>
{
    async fn handle(&mut self) -> Result<Option<HandlerOutcome<AmsMessage>>, HandlerError> {
        Err(HandlerError::NotImplemented)
    }
}
