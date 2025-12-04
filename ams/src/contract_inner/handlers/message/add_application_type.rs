use crate::interfaces::state::StateInterface;
use abi::ams::AmsMessage;
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::Account;
use runtime::interfaces::{access_control::AccessControl, contract::ContractRuntimeContext};
use std::{cell::RefCell, rc::Rc};

pub struct AddApplicationTypeHandler<R: ContractRuntimeContext + AccessControl, S: StateInterface> {
    _runtime: Rc<RefCell<R>>,
    state: S,

    owner: Account,
    application_type: String,
}

impl<R: ContractRuntimeContext + AccessControl, S: StateInterface> AddApplicationTypeHandler<R, S> {
    pub fn new(
        runtime: Rc<RefCell<R>>,
        state: S,
        owner: Account,
        application_type: String,
    ) -> Self {
        Self {
            state,
            _runtime: runtime,

            owner,
            application_type,
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl, S: StateInterface> Handler<AmsMessage>
    for AddApplicationTypeHandler<R, S>
{
    async fn handle(&mut self) -> Result<Option<HandlerOutcome<AmsMessage>>, HandlerError> {
        match self
            .state
            .add_application_type(self.owner, self.application_type.clone())
            .await
        {
            Ok(_) => Ok(None),
            Err(err) => Err(HandlerError::ProcessError(Box::new(err))),
        }
    }
}
