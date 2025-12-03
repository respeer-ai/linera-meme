use super::AmsContract;

use abi::ams::{AmsMessage, AmsOperation, AmsResponse};

use ams::{contract_inner::handlers::HandlerFactory, state::adapter::StateAdapter};
use runtime::contract::ContractRuntimeAdapter;

impl AmsContract {
    pub async fn on_op(&mut self, op: &AmsOperation) -> AmsResponse {
        let runtime_context = ContractRuntimeAdapter::new(self.runtime.clone());
        let state_adapter = StateAdapter::new(self.state.clone());

        let _outcome = match HandlerFactory::new(runtime_context, state_adapter, Some(op), None)
            .unwrap()
            .handle()
            .await
        {
            Ok(outcome) => outcome,
            Err(err) => panic!("Failed OP: {:?}: {err}", op),
        };

        // There won't be any message or event here
        AmsResponse::Ok
    }

    pub fn on_message(&mut self, msg: &AmsMessage) {
        let runtime_context = ContractRuntimeAdapter::new(self.runtime.clone());
        let state_adapter = StateAdapter::new(self.state.clone());

        let _outcome = match HandlerFactory::new(runtime_context, state_adapter, None, Some(msg)) {
            Ok(outcome) => outcome,
            Err(err) => panic!("Failed MSG {:?}: {err}", msg),
        };
    }
}
