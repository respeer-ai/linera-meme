use super::MemeContract;
use std::{cell::RefCell, rc::Rc};

use abi::meme::{InstantiationArgument, MemeMessage, MemeOperation, MemeResponse};

use meme::{
    contract_inner::{handlers::HandlerFactory, instantiation_handler::InstantiationHandler},
    state::adapter::StateAdapter,
};
use runtime::{contract::ContractRuntimeAdapter, interfaces::contract::ContractRuntimeContext};

impl MemeContract {
    pub async fn _instantiate(&mut self, argument: InstantiationArgument) {
        let runtime_context = Rc::new(RefCell::new(ContractRuntimeAdapter::new(
            self.runtime.clone(),
        )));

        let state_adapter = StateAdapter::new(self.state.clone());

        let Some(mut outcome) =
            InstantiationHandler::new(runtime_context.clone(), state_adapter, argument)
                .instantiate()
                .await
                .expect("Failed instantiate")
        else {
            return;
        };

        while let Some(message) = outcome.messages.pop() {
            log::debug!("DEBUG OP:MEME: sending message {:?} ", message);

            runtime_context
                .borrow_mut()
                .send_message(*message.destination(), message.message().clone());
        }
    }

    pub async fn on_op(&mut self, op: &MemeOperation) -> MemeResponse {
        let runtime_context = Rc::new(RefCell::new(ContractRuntimeAdapter::new(
            self.runtime.clone(),
        )));

        let state_adapter = StateAdapter::new(self.state.clone());

        log::info!("DEBUG OP:MEME: processing {:?}", op);

        let mut outcome =
            match HandlerFactory::new(runtime_context.clone(), state_adapter, Some(op), None)
                .expect("Failed: construct operation handler")
                .handle()
                .await
            {
                Ok(Some(outcome)) => outcome,
                Ok(None) => return MemeResponse::Ok,
                Err(err) => panic!("Failed OP {:?}: {err}", op),
            };

        log::debug!("DEBUG OP:MEME: processed {:?}", op);

        while let Some(message) = outcome.messages.pop() {
            log::debug!("DEBUG OP:MEME: sending message {:?} ", message);

            runtime_context
                .borrow_mut()
                .send_message(*message.destination(), message.message().clone());
        }

        // TODO: process event / stream

        outcome.response.unwrap_or(MemeResponse::Ok)
    }

    pub async fn on_message(&mut self, msg: &MemeMessage) {
        let runtime_context = Rc::new(RefCell::new(ContractRuntimeAdapter::new(
            self.runtime.clone(),
        )));
        let state_adapter = StateAdapter::new(self.state.clone());

        log::info!("DEBUG MSG:MEME: processing {:?}", msg);

        let mut outcome =
            match HandlerFactory::new(runtime_context.clone(), state_adapter, None, Some(msg))
                .expect("Failed: construct message handler")
                .handle()
                .await
            {
                Ok(Some(outcome)) => outcome,
                Ok(None) => return,
                Err(err) => panic!("Failed MSG {:?}: {err}", msg),
            };

        log::debug!("DEBUG MSG:MEME: processed {:?}", msg);

        while let Some(message) = outcome.messages.pop() {
            log::debug!("DEBUG MSG:MEME: sending message {:?} ", message);

            runtime_context
                .borrow_mut()
                .send_message(*message.destination(), message.message().clone());
        }

        // TODO: process event / stream
    }
}
