use super::PoolStateContract;
use std::{cell::RefCell, rc::Rc};

use abi::pool::state_v1::{PoolStateV1Operation, PoolStateV1Response, StateInstantiationArgument};
use base::handler::HandlerOutcome;
use pool_state::{
    contract_inner::handlers::HandlerFactory, interfaces::state::StateInterface,
    state::adapter::StateAdapter,
};
use runtime::{contract::ContractRuntimeAdapter, interfaces::contract::ContractRuntimeContext};

impl PoolStateContract {
    pub fn _instantiate(&mut self, argument: StateInstantiationArgument) {
        self.state
            .borrow_mut()
            .instantiate(argument)
            .expect("Failed to instantiate pool state v1");
    }

    pub async fn on_op(&mut self, op: &PoolStateV1Operation) -> PoolStateV1Response {
        let runtime_context = Rc::new(RefCell::new(ContractRuntimeAdapter::new(
            self.runtime.clone(),
        )));
        let state_adapter = StateAdapter::new(self.state.clone());

        let outcome =
            match HandlerFactory::new(runtime_context.clone(), state_adapter, Some(op), None)
                .expect("Failed: construct pool state v1 operation handler")
                .handle()
                .await
            {
                Ok(Some(outcome)) => outcome,
                Ok(None) => return PoolStateV1Response::Ok,
                Err(error) => {
                    return PoolStateV1Response::Fail(format!(
                        "Failed pool state v1 operation {:?}: {error}",
                        op
                    ))
                }
            };

        Self::apply_outcome(runtime_context, outcome)
    }

    fn apply_outcome(
        runtime_context: Rc<RefCell<impl ContractRuntimeContext<Message = ()>>>,
        mut outcome: HandlerOutcome<(), PoolStateV1Response>,
    ) -> PoolStateV1Response {
        while let Some(message) = outcome.messages.pop() {
            runtime_context.borrow_mut().send_message(
                *message.destination(),
                *message.message(),
                message.tracking(),
            );
        }

        outcome.response.unwrap_or(PoolStateV1Response::Ok)
    }
}
