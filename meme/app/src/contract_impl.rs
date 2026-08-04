use super::MemeContract;
use abi::meme::{MemeMessage, MemeOperation, MemeResponse};
use meme_app::{contract_inner::handlers::HandlerFactory, state::adapter::ContractStateAdapter};
use runtime::{contract::ContractRuntimeAdapter, interfaces::contract::ContractRuntimeContext};
use std::{cell::RefCell, rc::Rc};

impl MemeContract {
    pub async fn on_op(&mut self, op: &MemeOperation) -> MemeResponse {
        let runtime_context = Rc::new(RefCell::new(ContractRuntimeAdapter::new(
            self.runtime.clone(),
        )));
        let state_adapter = ContractStateAdapter::new(runtime_context.clone(), self.state.clone());

        let mut outcome =
            match HandlerFactory::new(runtime_context.clone(), state_adapter, Some(op), None)
                .expect("Failed: construct Meme operation handler")
                .handle()
                .await
            {
                Ok(Some(outcome)) => outcome,
                Ok(None) => return MemeResponse::Ok,
                Err(err) => panic!("Failed Meme operation {:?}: {err}", op),
            };

        while let Some(message) = outcome.messages.pop() {
            runtime_context.borrow_mut().send_message(
                *message.destination(),
                message.message().clone(),
                message.tracking(),
            );
        }

        outcome.response.unwrap_or(MemeResponse::Ok)
    }

    pub async fn on_message(&mut self, msg: &MemeMessage) {
        let runtime_context = Rc::new(RefCell::new(ContractRuntimeAdapter::new(
            self.runtime.clone(),
        )));
        let state_adapter = ContractStateAdapter::new(runtime_context.clone(), self.state.clone());

        let mut outcome =
            match HandlerFactory::new(runtime_context.clone(), state_adapter, None, Some(msg))
                .expect("Failed: construct Meme message handler")
                .handle()
                .await
            {
                Ok(Some(outcome)) => outcome,
                Ok(None) => return,
                Err(err) => panic!("Failed Meme message {:?}: {err}", msg),
            };

        while let Some(message) = outcome.messages.pop() {
            runtime_context.borrow_mut().send_message(
                *message.destination(),
                message.message().clone(),
                message.tracking(),
            );
        }
    }
}
