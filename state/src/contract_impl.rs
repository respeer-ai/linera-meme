use super::StateContract;
use abi::state::{StateMessage, StateOperation, StateResponse};
use base::handler::HandlerOutcome;
use runtime::contract::ContractRuntimeAdapter;
use runtime::interfaces::contract::ContractRuntimeContext;
use state::{contract_inner::handlers::HandlerFactory, state::adapter::StateAdapter};
use std::{cell::RefCell, rc::Rc};

impl StateContract {
    pub async fn on_op(&mut self, operation: &StateOperation) -> StateResponse {
        let runtime_context = Rc::new(RefCell::new(ContractRuntimeAdapter::new(
            self.runtime.clone(),
        )));
        let state_adapter = StateAdapter::new(self.state.clone());

        log::debug!("DEBUG OP:STATE: processing {:?}", operation);

        let outcome = match HandlerFactory::new(
            runtime_context.clone(),
            state_adapter,
            Some(operation),
            None,
        )
        .unwrap()
        .handle()
        .await
        {
            Ok(Some(outcome)) => outcome,
            Ok(None) => return StateResponse::Ok,
            Err(err) => panic!("Failed OP: {:?}: {err}", operation),
        };

        log::debug!("DEBUG OP:STATE: processed {:?}", operation);

        Self::apply_outcome(runtime_context, outcome)
    }

    pub async fn on_message(&mut self, message: &StateMessage) {
        let runtime_context = Rc::new(RefCell::new(ContractRuntimeAdapter::new(
            self.runtime.clone(),
        )));
        let state_adapter = StateAdapter::new(self.state.clone());

        log::debug!("DEBUG MSG:STATE: processing {:?}", message);

        let outcome =
            match HandlerFactory::new(runtime_context.clone(), state_adapter, None, Some(message))
                .unwrap()
                .handle()
                .await
            {
                Ok(Some(outcome)) => outcome,
                Ok(None) => return,
                Err(err) => panic!("Failed MSG {:?}: {err}", message),
            };

        log::debug!("DEBUG MSG:STATE: processed {:?}", message);

        Self::apply_outcome(runtime_context, outcome);
    }

    fn apply_outcome(
        runtime_context: Rc<RefCell<impl ContractRuntimeContext<Message = StateMessage>>>,
        mut outcome: HandlerOutcome<StateMessage, StateResponse>,
    ) -> StateResponse {
        while let Some(message) = outcome.messages.pop() {
            runtime_context.borrow_mut().send_message(
                *message.destination(),
                message.message().clone(),
                message.tracking(),
            );
        }

        outcome.response.unwrap_or(StateResponse::Ok)
    }
}
