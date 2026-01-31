use super::PoolContract;
use std::{cell::RefCell, rc::Rc};

use abi::swap::pool::{InstantiationArgument, PoolMessage, PoolOperation, PoolResponse};

use linera_sdk::linera_base_types::Amount;
use pool::{
    contract_inner::handlers::HandlerFactory,
    interfaces::{parameters::ParametersInterface, state::StateInterface},
    state::adapter::StateAdapter,
};
use runtime::{
    contract::ContractRuntimeAdapter,
    interfaces::{base::BaseRuntimeContext, contract::ContractRuntimeContext},
};

impl PoolContract {
    pub async fn _instantiate(&mut self, argument: InstantiationArgument) {
        let mut runtime_context = ContractRuntimeAdapter::new(self.runtime.clone());

        let parameters = runtime_context.application_parameters();

        let creator = runtime_context.creator();
        let timestamp = runtime_context.system_time();
        let liquidity = self
            .state
            .borrow_mut()
            .instantiate(argument.clone(), parameters, creator, timestamp)
            .await
            .expect("Failed instantiate");

        if argument.amount_0 <= Amount::ZERO || argument.amount_1 <= Amount::ZERO {
            return;
        }

        let transaction = self.state.borrow().build_transaction(
            creator,
            Some(argument.amount_0),
            Some(argument.amount_1),
            None,
            None,
            Some(liquidity),
            timestamp,
        );
        let chain_id = runtime_context.chain_id();
        runtime_context.send_message(chain_id, PoolMessage::NewTransaction { transaction });
    }

    pub async fn on_op(&mut self, op: &PoolOperation) -> PoolResponse {
        let runtime_context = Rc::new(RefCell::new(ContractRuntimeAdapter::new(
            self.runtime.clone(),
        )));
        let state_adapter = StateAdapter::new(self.state.clone());

        log::info!("DEBUG OP:POOL: processing {:?}", op);

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

        log::debug!("DEBUG OP:POOL: processed {:?}", op);

        while let Some(message) = outcome.messages.pop() {
            log::debug!("DEBUG OP:POOL: sending message {:?} ", message);

            runtime_context
                .borrow_mut()
                .send_message(*message.destination(), message.message().clone());
        }

        // TODO: process event / stream

        PoolResponse::Ok
    }

    pub async fn on_message(&mut self, msg: &PoolMessage) {
        let runtime_context = Rc::new(RefCell::new(ContractRuntimeAdapter::new(
            self.runtime.clone(),
        )));
        let state_adapter = StateAdapter::new(self.state.clone());

        log::info!("DEBUG MSG:POOL: processing {:?}", msg);

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

        log::debug!("DEBUG MSG:POOL: processed {:?}", msg);

        while let Some(message) = outcome.messages.pop() {
            log::debug!("DEBUG MSG:POOL: sending message {:?} ", message);

            runtime_context
                .borrow_mut()
                .send_message(*message.destination(), message.message().clone());
        }

        // TODO: process event / stream
    }
}
