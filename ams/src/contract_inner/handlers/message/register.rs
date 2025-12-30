use crate::interfaces::state::StateInterface;
use abi::ams::{AmsMessage, AmsResponse, Metadata};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use runtime::interfaces::{access_control::AccessControl, contract::ContractRuntimeContext};
use std::{cell::RefCell, rc::Rc};

pub struct RegisterHandler<R: ContractRuntimeContext + AccessControl, S: StateInterface> {
    _runtime: Rc<RefCell<R>>,
    state: S,

    metadata: Metadata,
}

impl<R: ContractRuntimeContext + AccessControl, S: StateInterface> RegisterHandler<R, S> {
    pub fn new(runtime: Rc<RefCell<R>>, state: S, msg: &AmsMessage) -> Self {
        let AmsMessage::Register { metadata } = msg else {
            panic!("Invalid message");
        };

        Self {
            state,
            _runtime: runtime,

            metadata: metadata.clone(),
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl, S: StateInterface> Handler<AmsMessage, AmsResponse>
    for RegisterHandler<R, S>
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<AmsMessage, AmsResponse>>, HandlerError> {
        match self.state.register_application(self.metadata.clone()) {
            Ok(_) => Ok(None),
            Err(err) => Err(HandlerError::ProcessError(Box::new(err))),
        }
    }
}
