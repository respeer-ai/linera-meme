use super::AmsContract;
use abi::{
    ams::{
        AmsKey, AmsMessage, AmsOperation, AmsResponse, InstantiationArgument, APPLICATION_TYPES,
    },
    namespace,
};
use ams::{
    contract_inner::handlers::HandlerFactory, interfaces::state::StateInterface,
    state::adapter::StateAdapter,
};
use runtime::{contract::ContractRuntimeAdapter, interfaces::contract::ContractRuntimeContext};
use state::{adapters::contract::StateContract, interfaces::contract::StateContractInterface};
use std::{cell::RefCell, rc::Rc};

impl AmsContract {
    pub async fn _instantiate(&mut self, argument: InstantiationArgument) {
        let account = ContractRuntimeAdapter::new(self.runtime.clone()).authenticated_account();
        let mut state_adapter = StateAdapter::new(self.state.clone());
        state_adapter.instantiate(account, argument);

        let state_app_id = state_adapter
            .state_app_id()
            .expect("Failed to read AMS state app id");
        let state_runtime = Rc::new(RefCell::new(ContractRuntimeAdapter::new(
            self.runtime.clone(),
        )));
        let mut state_contract = StateContract::new(state_runtime, state_app_id, namespace::AMS);
        state_contract
            .initialize_operator()
            .await
            .expect("Failed to initialize AMS state operator");
        state_contract
            .create_namespace()
            .await
            .expect("Failed to create AMS state namespace");
        state_contract
            .write(&AmsKey::Operator, &account)
            .await
            .expect("Failed to write AMS operator to state");

        let application_types = APPLICATION_TYPES
            .iter()
            .map(|application_type| application_type.to_string())
            .collect::<Vec<_>>();
        state_contract
            .write(&AmsKey::ApplicationTypes, &application_types)
            .await
            .expect("Failed to write AMS application types to state");
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

            runtime_context.borrow_mut().send_message(
                *message.destination(),
                message.message().clone(),
                message.tracking(),
            );
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
            runtime_context.borrow_mut().send_message(
                *message.destination(),
                message.message().clone(),
                message.tracking(),
            );
        }

        // TODO: process event / stream
    }
}
