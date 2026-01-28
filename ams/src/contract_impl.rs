use super::AmsContract;
use abi::ams::{AmsMessage, AmsOperation, AmsResponse, InstantiationArgument};
use ams::{
    contract_inner::handlers::HandlerFactory, interfaces::state::StateInterface,
    state::adapter::StateAdapter,
};
use runtime::{contract::ContractRuntimeAdapter, interfaces::contract::ContractRuntimeContext};
use std::{cell::RefCell, rc::Rc};

impl AmsContract {
    pub fn _instantiate(&mut self, argument: InstantiationArgument) {
        let account = ContractRuntimeAdapter::new(self.runtime.clone()).authenticated_account();
        self.state.borrow_mut().instantiate(account, argument);
    }

    pub async fn on_op(&mut self, op: &AmsOperation) -> AmsResponse {
        let runtime_context = Rc::new(RefCell::new(ContractRuntimeAdapter::new(
            self.runtime.clone(),
        )));
        let state_adapter = StateAdapter::new(self.state.clone());

        log::debug!("DEBUG OP:AMS: processing {:?}", op);

        let mut outcome =
            match HandlerFactory::new(runtime_context.clone(), state_adapter, Some(op), None)
                .unwrap()
                .handle()
                .await
            {
                Ok(Some(outcome)) => outcome,
                Ok(None) => return AmsResponse::Ok,
                Err(err) => panic!("Failed OP: {:?}: {err}", op),
            };

        log::debug!("DEBUG OP:AMS: processed {:?}", op);

        while let Some(message) = outcome.messages.pop() {
            log::debug!("DEBUG OP:AMS: sending message {:?} ", message);

            runtime_context
                .borrow_mut()
                .send_message(*message.destination(), message.message().clone());
        }

        // TODO: process event / stream

        AmsResponse::Ok
    }

    pub async fn on_message(&mut self, msg: &AmsMessage) {
        let runtime_context = Rc::new(RefCell::new(ContractRuntimeAdapter::new(
            self.runtime.clone(),
        )));
        let state_adapter = StateAdapter::new(self.state.clone());

        log::debug!("DEBUG MSG:AMS: processing {:?}", msg);

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

        log::debug!("DEBUG MSG:AMS: processed {:?}", msg);

        while let Some(message) = outcome.messages.pop() {
            runtime_context
                .borrow_mut()
                .send_message(*message.destination(), message.message().clone());
        }

        // TODO: process event / stream
    }
}
