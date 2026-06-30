use super::AmsStateContract;
use std::{cell::RefCell, rc::Rc};

use abi::ams::state_v1::{AmsStateOperation, AmsStateResponse, StateInstantiationArgument};
use ams_state::{
    contract_inner::handlers::HandlerFactory, interfaces::state::StateInterface,
    state::adapter::StateAdapter,
};
use base::handler::HandlerOutcome;
use runtime::{contract::ContractRuntimeAdapter, interfaces::contract::ContractRuntimeContext};

impl AmsStateContract {
    pub fn _instantiate(&mut self, argument: StateInstantiationArgument) {
        self.state.borrow_mut().instantiate(argument);
    }

    pub async fn on_op(&mut self, op: &AmsStateOperation) -> AmsStateResponse {
        let runtime_context = Rc::new(RefCell::new(ContractRuntimeAdapter::new(
            self.runtime.clone(),
        )));
        let state_adapter = StateAdapter::new(self.state.clone());

        let outcome =
            match HandlerFactory::new(runtime_context.clone(), state_adapter, Some(op), None)
                .expect("Failed: construct AMS StateV1 operation handler")
                .handle()
                .await
            {
                Ok(Some(outcome)) => outcome,
                Ok(None) => return AmsStateResponse::Ok,
                Err(error) => panic!("Failed AMS StateV1 operation {:?}: {error}", op),
            };

        Self::apply_outcome(runtime_context, outcome)
    }

    fn apply_outcome(
        runtime_context: Rc<RefCell<impl ContractRuntimeContext<Message = ()>>>,
        mut outcome: HandlerOutcome<(), AmsStateResponse>,
    ) -> AmsStateResponse {
        while let Some(message) = outcome.messages.pop() {
            runtime_context.borrow_mut().send_message(
                *message.destination(),
                *message.message(),
                message.tracking(),
            );
        }

        outcome.response.unwrap_or(AmsStateResponse::Ok)
    }
}
