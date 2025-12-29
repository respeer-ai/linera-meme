use super::ProxyContract;
use std::{cell::RefCell, rc::Rc};

use abi::proxy::{InstantiationArgument, ProxyMessage, ProxyOperation, ProxyResponse};

use proxy::{
    contract_inner::handlers::HandlerFactory, interfaces::state::StateInterface,
    state::adapter::StateAdapter,
};
use runtime::{
    contract::ContractRuntimeAdapter,
    interfaces::{base::BaseRuntimeContext, contract::ContractRuntimeContext},
};

impl ProxyContract {
    pub async fn _instantiate(&mut self, argument: InstantiationArgument) {
        let mut runtime_context = ContractRuntimeAdapter::new(self.runtime.clone());

        let _ = runtime_context.application_parameters();

        let owners = runtime_context.owner_accounts();

        self.state
            .borrow_mut()
            .instantiate(argument.clone(), owners)
            .await
            .expect("Failed instantiate");
    }

    pub async fn on_op(&mut self, op: &ProxyOperation) -> ProxyResponse {
        let runtime_context = Rc::new(RefCell::new(ContractRuntimeAdapter::new(
            self.runtime.clone(),
        )));

        let state_adapter = StateAdapter::new(self.state.clone());

        log::warn!("DEBUG OP:SWAP: processing {:?}", op);

        let mut outcome =
            match HandlerFactory::new(runtime_context.clone(), state_adapter, Some(op), None)
                .expect("Failed: construct operation handler")
                .handle()
                .await
            {
                Ok(Some(outcome)) => outcome,
                Ok(None) => return ProxyResponse::Ok,
                Err(err) => panic!("Failed OP: {:?}: {err}", op),
            };

        log::warn!("DEBUG OP:SWAP: processed {:?}", op);

        while let Some(message) = outcome.messages.pop() {
            log::warn!("DEBUG OP:SWAP: sending message {:?} ", message);

            runtime_context
                .borrow_mut()
                .send_message(*message.destination(), message.message().clone());
        }

        // TODO: process event / stream

        ProxyResponse::Ok
    }

    pub async fn on_message(&mut self, msg: &ProxyMessage) {
        let runtime_context = Rc::new(RefCell::new(ContractRuntimeAdapter::new(
            self.runtime.clone(),
        )));
        let state_adapter = StateAdapter::new(self.state.clone());

        log::warn!("DEBUG MSG:SWAP: processing {:?}", msg);

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

        log::warn!("DEBUG MSG:SWAP: processed {:?}", msg);

        while let Some(message) = outcome.messages.pop() {
            log::warn!("DEBUG MSG:SWAP: sending message {:?} ", message);

            runtime_context
                .borrow_mut()
                .send_message(*message.destination(), message.message().clone());
        }

        // TODO: process event / stream
    }
}
