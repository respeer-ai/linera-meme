use crate::interfaces::state::StateInterface;
use abi::ams::{AmsMessage, AmsOperation, AmsResponse, Metadata};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::ApplicationId;
use runtime::interfaces::{access_control::AccessControl, contract::ContractRuntimeContext};
use std::{cell::RefCell, rc::Rc};

pub struct UpdateHandler<R: ContractRuntimeContext + AccessControl, S: StateInterface> {
    _runtime: Rc<RefCell<R>>,
    _state: S,

    _application_id: ApplicationId,
    _metadata: Metadata,
}

impl<R: ContractRuntimeContext + AccessControl, S: StateInterface> UpdateHandler<R, S> {
    pub fn new(runtime: Rc<RefCell<R>>, state: S, op: &AmsOperation) -> Self {
        let AmsOperation::Update {
            application_id,
            metadata,
        } = op
        else {
            panic!("Invalid operation");
        };

        Self {
            _state: state,
            _runtime: runtime,

            _application_id: *application_id,
            _metadata: metadata.clone(),
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
        Err(HandlerError::NotImplemented)
    }
}
