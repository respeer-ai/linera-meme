use super::BlobGatewayContract;
use std::{cell::RefCell, rc::Rc};

use abi::blob_gateway::{BlobGatewayMessage, BlobGatewayOperation, BlobGatewayResponse};

use blob_gateway::{contract_inner::handlers::HandlerFactory, state::adapter::StateAdapter};
use runtime::{contract::ContractRuntimeAdapter, interfaces::contract::ContractRuntimeContext};

impl BlobGatewayContract {
    pub async fn on_op(&mut self, op: &BlobGatewayOperation) -> BlobGatewayResponse {
        let runtime_context = Rc::new(RefCell::new(ContractRuntimeAdapter::new(
            self.runtime.clone(),
        )));
        let state_adapter = StateAdapter::new(self.state.clone());

        log::info!("DEBUG OP:BLOB GATEWAY: processing {:?}", op);

        let mut outcome =
            match HandlerFactory::new(runtime_context.clone(), state_adapter, Some(op), None)
                .unwrap()
                .handle()
                .await
            {
                Ok(Some(outcome)) => outcome,
                Ok(None) => return BlobGatewayResponse::Ok,
                Err(err) => panic!("Failed OP: {:?}: {err}", op),
            };

        log::info!("DEBUG OP:BLOB GATEWAY: processed {:?}", op);

        while let Some(message) = outcome.messages.pop() {
            log::info!("DEBUG OP:BLOB GATEWAY: sending message {:?} ", message);

            runtime_context
                .borrow_mut()
                .send_message(*message.destination(), message.message().clone());
        }

        // TODO: process event / stream

        BlobGatewayResponse::Ok
    }

    pub async fn on_message(&mut self, msg: &BlobGatewayMessage) {
        let runtime_context = Rc::new(RefCell::new(ContractRuntimeAdapter::new(
            self.runtime.clone(),
        )));
        let state_adapter = StateAdapter::new(self.state.clone());

        log::info!("DEBUG MSG:BLOB GATEWAY: processing {:?}", msg);

        let mut outcome =
            match HandlerFactory::new(runtime_context.clone(), state_adapter, None, Some(msg))
                .unwrap()
                .handle()
                .await
            {
                Ok(Some(outcome)) => outcome,
                Ok(None) => return,
                Err(err) => panic!("Failed MSG {:?}: {err}", msg),
            };

        log::info!("DEBUG MSG:BLOB GATEWAY: processed {:?}", msg);

        while let Some(message) = outcome.messages.pop() {
            runtime_context
                .borrow_mut()
                .send_message(*message.destination(), message.message().clone());
        }

        // TODO: process event / stream
    }
}
