use abi::blob_gateway::{
    state_v1::{BlobGatewayStateV1Operation, BlobGatewayStateV1Response},
    BlobData,
};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use runtime::interfaces::{access_control::AccessControl, contract::ContractRuntimeContext};
use std::{cell::RefCell, rc::Rc};

use crate::interfaces::state::StateInterface;

pub struct CreateBlobHandler<R: ContractRuntimeContext + AccessControl, S: StateInterface> {
    runtime: Rc<RefCell<R>>,
    state: S,
    blob_data: BlobData,
}

impl<R: ContractRuntimeContext + AccessControl, S: StateInterface> CreateBlobHandler<R, S> {
    pub fn new(runtime: Rc<RefCell<R>>, state: S, operation: &BlobGatewayStateV1Operation) -> Self {
        let BlobGatewayStateV1Operation::CreateBlob { blob_data } = operation else {
            panic!("Invalid operation");
        };
        Self {
            runtime,
            state,
            blob_data: blob_data.clone(),
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl, S: StateInterface>
    Handler<(), BlobGatewayStateV1Response> for CreateBlobHandler<R, S>
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

        self.state
            .create_blob(self.blob_data.clone())
            .await
            .map_err(|error| HandlerError::ProcessError(error.into()))?;

        Ok(None)
    }
}
