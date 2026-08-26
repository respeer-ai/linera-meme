use super::ProxyStateContract;
use std::{cell::RefCell, rc::Rc};

use abi::proxy::state_v1::{
    ProxyStateV1Operation, ProxyStateV1Response, StateInstantiationArgument,
};
use base::handler::HandlerOutcome;
use proxy_state::{
    contract_inner::handlers::HandlerFactory, interfaces::state::StateInterface,
    state::adapter::StateAdapter,
};
use runtime::{contract::ContractRuntimeAdapter, interfaces::contract::ContractRuntimeContext};

impl ProxyStateContract {
    pub fn _instantiate(&mut self, argument: StateInstantiationArgument) {
        self.state
            .borrow_mut()
            .instantiate(argument)
            .expect("Failed to instantiate proxy state v1");
    }

    pub async fn on_op(&mut self, op: &ProxyStateV1Operation) -> ProxyStateV1Response {
        let runtime_context = Rc::new(RefCell::new(ContractRuntimeAdapter::new(
            self.runtime.clone(),
        )));
        let state_adapter = StateAdapter::new(self.state.clone());

        let outcome =
            match HandlerFactory::new(runtime_context.clone(), state_adapter, Some(op), None)
                .expect("Failed: construct proxy state v1 operation handler")
                .handle()
                .await
            {
                Ok(Some(outcome)) => outcome,
                Ok(None) => return ProxyStateV1Response::Ok,
                Err(error) => {
                    return ProxyStateV1Response::Fail(format!(
                        "Failed proxy state v1 operation {:?}: {error}",
                        op
                    ))
                }
            };

        Self::apply_outcome(runtime_context, outcome)
    }

    fn apply_outcome(
        runtime_context: Rc<RefCell<impl ContractRuntimeContext<Message = ()>>>,
        mut outcome: HandlerOutcome<(), ProxyStateV1Response>,
    ) -> ProxyStateV1Response {
        while let Some(message) = outcome.messages.pop() {
            runtime_context.borrow_mut().send_message(
                *message.destination(),
                *message.message(),
                message.tracking(),
            );
        }

        outcome.response.unwrap_or(ProxyStateV1Response::Ok)
    }
}
