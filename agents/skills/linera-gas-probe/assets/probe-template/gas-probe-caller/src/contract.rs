#![cfg_attr(target_arch = "wasm32", no_main)]

use gas_probe_abi::{
    decode_payload, encode_payload, GasProbeCalleeOperation, GasProbeCallerAbi,
    GasProbeCallerOperation, GasProbeResponse,
};
use linera_sdk::{
    linera_base_types::WithContractAbi,
    views::{RootView, View},
    Contract, ContractRuntime,
};

mod state;

use state::GasProbeCallerState;

pub struct GasProbeCallerContract {
    runtime: ContractRuntime<Self>,
    state: GasProbeCallerState,
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
        let state = GasProbeCallerState::load(runtime.root_view_storage_context())
            .await
            .expect("failed to load caller state");
        Self { runtime, state }
    }

    async fn instantiate(&mut self, _argument: Self::InstantiationArgument) {
        seed_state(&mut self.state).expect("failed to seed caller state");
    }

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
            GasProbeCallerOperation::DirectStateRead {
                payload_size,
                iterations,
            } => {
                for iteration in 0..iterations {
                    let _bytes = self
                        .state
                        .bytes_by_size
                        .get(&read_key(payload_size, iteration))
                        .await
                        .expect("failed to read caller state")
                        .expect("missing seeded caller state");
                }
                GasProbeResponse::Ok
            }
            GasProbeCallerOperation::DirectStateWrite {
                payload_size,
                iterations,
            } => {
                let payload = vec![7; payload_size as usize];
                for iteration in 0..iterations {
                    self.state
                        .bytes_by_size
                        .insert(&write_key(payload_size, iteration), payload.clone())
                        .expect("failed to write caller state");
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
            GasProbeCallerOperation::CallApplicationStateRead {
                callee,
                payload_size,
                iterations,
            } => {
                for iteration in 0..iterations {
                    let _response = self.runtime.call_application(
                        true,
                        callee,
                        &GasProbeCalleeOperation::StateRead {
                            payload_size,
                            iteration,
                        },
                    );
                }
                GasProbeResponse::Ok
            }
            GasProbeCallerOperation::CallApplicationStateWrite {
                callee,
                payload_size,
                iterations,
            } => {
                for iteration in 0..iterations {
                    let _response = self.runtime.call_application(
                        true,
                        callee,
                        &GasProbeCalleeOperation::StateWrite {
                            payload_size,
                            iteration,
                        },
                    );
                }
                GasProbeResponse::Ok
            }
        }
    }

    async fn execute_message(&mut self, _message: Self::Message) {}

    async fn store(mut self) {
        self.state
            .save()
            .await
            .expect("failed to save caller state");
    }
}

fn seed_state(state: &mut GasProbeCallerState) -> Result<(), linera_sdk::views::ViewError> {
    for size in [32, 512, 2048] {
        for iteration in 0..10 {
            state
                .bytes_by_size
                .insert(&read_key(size, iteration), vec![7; size as usize])?;
        }
    }
    Ok(())
}

fn read_key(payload_size: u32, iteration: u32) -> u32 {
    payload_size * 1_000 + iteration
}

fn write_key(payload_size: u32, iteration: u32) -> u32 {
    payload_size * 1_000 + 100 + iteration
}
