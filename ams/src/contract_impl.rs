use super::AmsContract;
use std::{cell::RefCell, rc::Rc};

use abi::ams::{AmsMessage, AmsOperation, AmsResponse};

use ams::{contract_inner::handlers::HandlerFactory, state::adapter::StateAdapter};
use runtime::{contract::ContractRuntimeAdapter, interfaces::contract::ContractRuntimeContext};

impl AmsContract {
    pub async fn on_op(&mut self, op: &AmsOperation) -> AmsResponse {
        let runtime_context = Rc::new(RefCell::new(ContractRuntimeAdapter::new(
            self.runtime.clone(),
        )));
        let state_adapter = StateAdapter::new(self.state.clone());

        let mut outcome =
            match HandlerFactory::new(runtime_context.clone(), state_adapter, Some(op), None)
                .unwrap()
                .handle()
                .await
            {
                Ok(outcome) => outcome,
                Err(err) => panic!("Failed OP: {:?}: {err}", op),
            };

        while let Some(message) = outcome.messages.pop() {
            runtime_context
                .borrow_mut()
                .send_message(*message.destination(), message.message().clone());
        }

        // TODO: process event / stream

        AmsResponse::Ok
    }

    pub fn on_message(&mut self, msg: &AmsMessage) {
        let runtime_context = Rc::new(RefCell::new(ContractRuntimeAdapter::new(
            self.runtime.clone(),
        )));
        let state_adapter = StateAdapter::new(self.state.clone());

        let _outcome = match HandlerFactory::new(runtime_context, state_adapter, None, Some(msg)) {
            Ok(outcome) => outcome,
            Err(err) => panic!("Failed MSG {:?}: {err}", msg),
        };
    }
}
