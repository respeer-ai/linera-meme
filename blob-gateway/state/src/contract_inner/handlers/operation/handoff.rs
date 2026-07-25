use abi::blob_gateway::state_v1::{BlobGatewayStateV1Operation, BlobGatewayStateV1Response};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::ApplicationId;
use runtime::interfaces::{access_control::AccessControl, contract::ContractRuntimeContext};
use std::{cell::RefCell, rc::Rc};

use crate::interfaces::state::StateInterface;

pub struct HandoffHandler<R: ContractRuntimeContext + AccessControl, S: StateInterface> {
    runtime: Rc<RefCell<R>>,
    state: S,
    new_business_application_id: ApplicationId,
}

impl<R: ContractRuntimeContext + AccessControl, S: StateInterface> HandoffHandler<R, S> {
    pub fn new(runtime: Rc<RefCell<R>>, state: S, operation: &BlobGatewayStateV1Operation) -> Self {
        let BlobGatewayStateV1Operation::Handoff {
            new_business_application_id,
        } = operation
        else {
            panic!("Invalid operation");
        };
        Self {
            runtime,
            state,
            new_business_application_id: *new_business_application_id,
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl, S: StateInterface>
    Handler<(), BlobGatewayStateV1Response> for HandoffHandler<R, S>
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<(), BlobGatewayStateV1Response>>, HandlerError> {
        self.runtime
            .borrow_mut()
            .only_caller_creator()
            .map_err(|error| HandlerError::RuntimeError(error.into()))?;

        let caller = self
            .runtime
            .borrow_mut()
            .require_authenticated_caller_id()
            .map_err(|error| HandlerError::RuntimeError(error.into()))?;

        let business_application_id = self
            .state
            .business_application_id()
            .await
            .map_err(|error| HandlerError::ProcessError(error.into()))?;

        if caller != business_application_id {
            return Err(HandlerError::NotAllowed);
        }

        let current_chain_id = self.runtime.borrow_mut().chain_id();
        let new_creator_chain_id = self
            .runtime
            .borrow_mut()
            .creator_chain_id(self.new_business_application_id);

        if new_creator_chain_id != current_chain_id {
            return Err(HandlerError::NotAllowed);
        }

        self.state
            .handoff(self.new_business_application_id)
            .await
            .map_err(|error| HandlerError::ProcessError(error.into()))?;

        let mut outcome = HandlerOutcome::new();
        outcome.with_response(BlobGatewayStateV1Response::Ok);
        Ok(Some(outcome))
    }
}
