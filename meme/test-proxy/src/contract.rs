#![cfg_attr(target_arch = "wasm32", no_main)]

use abi::meme::{MemeAbi, MemeOperation};
use linera_sdk::{
    linera_base_types::{WithContractAbi},
    Contract, ContractRuntime,
};
use meme_test_proxy::{FakeProxyAbi, FakeProxyOperation, FakeProxyResponse};

pub struct FakeProxyContract {
    runtime: ContractRuntime<Self>,
}

linera_sdk::contract!(FakeProxyContract);

impl WithContractAbi for FakeProxyContract {
    type Abi = FakeProxyAbi;
}

impl Contract for FakeProxyContract {
    type Message = ();
    type Parameters = ();
    type InstantiationArgument = ();
    type EventValue = ();

    async fn load(runtime: ContractRuntime<Self>) -> Self {
        Self { runtime }
    }

    async fn instantiate(&mut self, _argument: ()) {}

    async fn execute_operation(
        &mut self,
        operation: FakeProxyOperation,
    ) -> FakeProxyResponse {
        match operation {
            FakeProxyOperation::InitializeMeme {
                meme_app_id,
                argument,
            } => {
                let _response = self.runtime.call_application(
                    true,
                    meme_app_id.with_abi::<MemeAbi>(),
                    &MemeOperation::Initialize { argument },
                );
                FakeProxyResponse::Ok
            }
        }
    }

    async fn execute_message(&mut self, _message: ()) {}

    async fn store(self) {}
}
