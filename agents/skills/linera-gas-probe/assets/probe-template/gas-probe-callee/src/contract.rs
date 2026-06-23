#![cfg_attr(target_arch = "wasm32", no_main)]

use gas_probe_abi::{decode_payload, GasProbeCalleeAbi, GasProbeCalleeOperation, GasProbeResponse};
use linera_sdk::{linera_base_types::WithContractAbi, Contract, ContractRuntime};

pub struct GasProbeCalleeContract;

linera_sdk::contract!(GasProbeCalleeContract);

impl WithContractAbi for GasProbeCalleeContract {
    type Abi = GasProbeCalleeAbi;
}

impl Contract for GasProbeCalleeContract {
    type Message = ();
    type InstantiationArgument = ();
    type Parameters = ();
    type EventValue = ();

    async fn load(_runtime: ContractRuntime<Self>) -> Self {
        Self
    }

    async fn instantiate(&mut self, _argument: Self::InstantiationArgument) {}

    async fn execute_operation(&mut self, operation: GasProbeCalleeOperation) -> Self::Response {
        match operation {
            GasProbeCalleeOperation::Noop => GasProbeResponse::Ok,
            GasProbeCalleeOperation::EchoBytes { payload } => GasProbeResponse::Bytes(payload),
            GasProbeCalleeOperation::DecodeBytes {
                payload_kind,
                payload,
            } => {
                decode_payload(payload_kind, &payload);
                GasProbeResponse::Ok
            }
        }
    }

    async fn execute_message(&mut self, _message: Self::Message) {}

    async fn store(self) {}
}
