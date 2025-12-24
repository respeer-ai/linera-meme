use super::SwapContract;
use std::{cell::RefCell, rc::Rc};

use abi::swap::{SwapMessage, SwapOperation, SwapResponse};

use runtime::{contract::ContractRuntimeAdapter, interfaces::contract::ContractRuntimeContext};
use swap::{contract_inner::handlers::HandlerFactory, state::adapter::StateAdapter};

impl SwapContract {
    pub async fn instantiate(&mut self, argument: InstantiationArgument) {}

    pub async fn on_op(&mut self, op: &SwapOperation) -> SwapResponse {
        let runtime_context = Rc::new(RefCell::new(ContractRuntimeAdapter::new(
            self.runtime.clone(),
        )));
        let state_adapter = StateAdapter::new(self.state.clone());

        log::info!("DEBUG OP:SWAP: processing {:?}", op);

        let mut outcome =
            match HandlerFactory::new(runtime_context.clone(), state_adapter, Some(op), None)
                .unwrap()
                .handle()
                .await
            {
                Ok(Some(outcome)) => outcome,
                Ok(None) => return SwapResponse::Ok,
                Err(err) => panic!("Failed OP: {:?}: {err}", op),
            };

        log::info!("DEBUG OP:SWAP: processed {:?}", op);

        while let Some(message) = outcome.messages.pop() {
            log::info!("DEBUG OP:SWAP: sending message {:?} ", message);

            runtime_context
                .borrow_mut()
                .send_message(*message.destination(), message.message().clone());
        }

        // TODO: process event / stream

        SwapResponse::Ok
    }

    pub async fn on_message(&mut self, msg: &SwapMessage) {
        let runtime_context = Rc::new(RefCell::new(ContractRuntimeAdapter::new(
            self.runtime.clone(),
        )));
        let state_adapter = StateAdapter::new(self.state.clone());

        log::info!("DEBUG MSG:SWAP: processing {:?}", msg);

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

        log::info!("DEBUG MSG:SWAP: processed {:?}", msg);

        while let Some(message) = outcome.messages.pop() {
            runtime_context
                .borrow_mut()
                .send_message(*message.destination(), message.message().clone());
        }

        // TODO: process event / stream
    }
}
