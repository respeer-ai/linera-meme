use super::PoolContract;
use std::{cell::RefCell, rc::Rc};

use abi::pool::{InstantiationArgument, PoolMessage, PoolOperation, PoolResponse};

use pool::{contract_inner::handlers::HandlerFactory, state::adapter::ContractStateAdapter};
use runtime::{contract::ContractRuntimeAdapter, interfaces::contract::ContractRuntimeContext};

impl PoolContract {
    pub async fn _instantiate(&mut self, _argument: InstantiationArgument) {}

    pub async fn on_op(&mut self, op: &PoolOperation) -> PoolResponse {
        let runtime_context = Rc::new(RefCell::new(ContractRuntimeAdapter::new(
            self.runtime.clone(),
        )));
        let state_runtime_context = Rc::new(RefCell::new(ContractRuntimeAdapter::new(
            self.runtime.clone(),
        )));
        let state_adapter = ContractStateAdapter::new(state_runtime_context, self.state.clone());

        let mut outcome =
            match HandlerFactory::new(runtime_context.clone(), state_adapter, Some(op), None)
                .expect("Failed: construct operation handler")
                .handle()
                .await
            {
                Ok(Some(outcome)) => outcome,
                Ok(None) => return PoolResponse::Ok,
                Err(err) => panic!("Failed OP: {:?}: {err}", op),
            };

        while let Some(message) = outcome.messages.pop() {
            runtime_context.borrow_mut().send_message(
                *message.destination(),
                message.message().clone(),
                message.tracking(),
            );
        }

        outcome.response.unwrap_or(PoolResponse::Ok)
    }

    pub async fn on_message(&mut self, msg: &PoolMessage) {
        let runtime_context = Rc::new(RefCell::new(ContractRuntimeAdapter::new(
            self.runtime.clone(),
        )));
        let state_runtime_context = Rc::new(RefCell::new(ContractRuntimeAdapter::new(
            self.runtime.clone(),
        )));
        let state_adapter = ContractStateAdapter::new(state_runtime_context, self.state.clone());

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

        while let Some(message) = outcome.messages.pop() {
            runtime_context.borrow_mut().send_message(
                *message.destination(),
                message.message().clone(),
                message.tracking(),
            );
        }
    }
}
