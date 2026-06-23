#![cfg_attr(target_arch = "wasm32", no_main)]

use gas_probe_abi::{
    decode_payload, encode_payload, GasProbeCalleeOperation, GasProbeCallerAbi,
    GasProbeCallerOperation, GasProbeResponse,
};
use linera_sdk::{linera_base_types::WithContractAbi, Contract, ContractRuntime};

pub struct GasProbeCallerContract {
    runtime: ContractRuntime<Self>,
}

linera_sdk::contract!(GasProbeCallerContract);

impl WithContractAbi for GasProbeCallerContract {
    type Abi = GasProbeCallerAbi;
}

impl Contract for GasProbeCallerContract {
    type Message = ();
    type InstantiationArgument = ();
    type Parameters = ();
    type EventValue = ();

    async fn load(runtime: ContractRuntime<Self>) -> Self {
        Self { runtime }
    }

    async fn instantiate(&mut self, _argument: Self::InstantiationArgument) {}

    async fn execute_operation(&mut self, operation: GasProbeCallerOperation) -> Self::Response {
        match operation {
            GasProbeCallerOperation::Noop => GasProbeResponse::Ok,
            GasProbeCallerOperation::BcsEncode {
                payload_kind,
                iterations,
            } => {
                for _ in 0..iterations {
                    let _bytes = encode_payload(payload_kind);
                }
                GasProbeResponse::Ok
            }
            GasProbeCallerOperation::BcsDecode {
                payload_kind,
                payload,
                iterations,
            } => {
                for _ in 0..iterations {
                    decode_payload(payload_kind, &payload);
                }
                GasProbeResponse::Ok
            }
            GasProbeCallerOperation::BcsRoundtrip {
                payload_kind,
                iterations,
            } => {
                for _ in 0..iterations {
                    let payload = encode_payload(payload_kind);
                    decode_payload(payload_kind, &payload);
                }
                GasProbeResponse::Ok
            }
            GasProbeCallerOperation::CallApplicationNoop { callee, iterations } => {
                for _ in 0..iterations {
                    let _response =
                        self.runtime
                            .call_application(true, callee, &GasProbeCalleeOperation::Noop);
                }
                GasProbeResponse::Ok
            }
            GasProbeCallerOperation::CallApplicationEcho {
                callee,
                payload_size,
                iterations,
            } => {
                let payload = vec![7; payload_size as usize];
                for _ in 0..iterations {
                    let _response = self.runtime.call_application(
                        true,
                        callee,
                        &GasProbeCalleeOperation::EchoBytes {
                            payload: payload.clone(),
                        },
                    );
                }
                GasProbeResponse::Ok
            }
            GasProbeCallerOperation::CallApplicationDecode {
                callee,
                payload_kind,
                iterations,
            } => {
                let payload = encode_payload(payload_kind);
                for _ in 0..iterations {
                    let _response = self.runtime.call_application(
                        true,
                        callee,
                        &GasProbeCalleeOperation::DecodeBytes {
                            payload_kind,
                            payload: payload.clone(),
                        },
                    );
                }
                GasProbeResponse::Ok
            }
        }
    }

    async fn execute_message(&mut self, _message: Self::Message) {}

    async fn store(self) {}
}
