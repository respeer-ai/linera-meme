#![cfg_attr(target_arch = "wasm32", no_main)]

use abi::ams::state_v1::{
    AmsStateAbi, AmsStateOperation, AmsStateResponse, StateInstantiationArgument,
};
use linera_sdk::views::linera_views;
use linera_sdk::{
    linera_base_types::{ApplicationId, WithContractAbi},
    views::{RegisterView, RootView, View, ViewStorageContext},
    Contract, ContractRuntime,
};

pub struct AmsStateContract {
    state: AmsState,
    runtime: ContractRuntime<Self>,
}

#[derive(RootView)]
#[view(context = ViewStorageContext)]
pub struct AmsState {
    pub business_application_id: RegisterView<Option<ApplicationId>>,
}

linera_sdk::contract!(AmsStateContract);

impl WithContractAbi for AmsStateContract {
    type Abi = AmsStateAbi;
}

impl Contract for AmsStateContract {
    type Message = ();
    type InstantiationArgument = StateInstantiationArgument;
    type Parameters = ();
    type EventValue = ();

    async fn load(runtime: ContractRuntime<Self>) -> Self {
        let state = AmsState::load(runtime.root_view_storage_context())
            .await
            .expect("Failed to load AMS StateV1 state");
        Self { state, runtime }
    }

    async fn instantiate(&mut self, argument: StateInstantiationArgument) {
        self.runtime.application_parameters();
        self.state
            .business_application_id
            .set(Some(argument.business_application_id));
    }

    async fn execute_operation(&mut self, _operation: AmsStateOperation) -> AmsStateResponse {
        todo!("AMS StateV1 operation handlers are implemented in later review diffs")
    }

    async fn execute_message(&mut self, _message: ()) {}

    async fn store(mut self) {
        self.state
            .save()
            .await
            .expect("Failed to save AMS StateV1 state");
    }
}
