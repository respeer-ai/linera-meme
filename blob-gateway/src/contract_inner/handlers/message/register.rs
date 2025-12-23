use crate::interfaces::state::StateInterface;
use abi::blob_gateway::{BlobData, BlobGatewayMessage};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use runtime::interfaces::{access_control::AccessControl, contract::ContractRuntimeContext};
use std::{cell::RefCell, rc::Rc};

pub struct RegisterHandler<R: ContractRuntimeContext + AccessControl, S: StateInterface> {
    _runtime: Rc<RefCell<R>>,
    state: S,

    blob_data: BlobData,
}

impl<R: ContractRuntimeContext + AccessControl, S: StateInterface> RegisterHandler<R, S> {
    pub fn new(runtime: Rc<RefCell<R>>, state: S, msg: &BlobGatewayMessage) -> Self {
        let BlobGatewayMessage::Register { blob_data } = msg;

        Self {
            state,
            _runtime: runtime,

            blob_data: blob_data.clone(),
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl, S: StateInterface> Handler<BlobGatewayMessage>
    for RegisterHandler<R, S>
{
    async fn handle(&mut self) -> Result<Option<HandlerOutcome<BlobGatewayMessage>>, HandlerError> {
        match self.state.create_blob(self.blob_data.clone()).await {
            Ok(_) => Ok(None),
            Err(err) => Err(HandlerError::ProcessError(Box::new(err))),
        }
    }
}
