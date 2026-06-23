#![cfg_attr(target_arch = "wasm32", no_main)]

use gas_probe_abi::{decode_payload, GasProbeCalleeAbi, GasProbeCalleeOperation, GasProbeResponse};
use linera_sdk::{
    linera_base_types::WithContractAbi,
    views::{RootView, View},
    Contract, ContractRuntime,
};

mod state;

use state::GasProbeCalleeState;

pub struct GasProbeCalleeContract {
    state: GasProbeCalleeState,
}

linera_sdk::contract!(GasProbeCalleeContract);

impl WithContractAbi for GasProbeCalleeContract {
    type Abi = GasProbeCalleeAbi;
}

impl Contract for GasProbeCalleeContract {
    type Message = ();
    type InstantiationArgument = ();
    type Parameters = ();
    type EventValue = ();

    async fn load(runtime: ContractRuntime<Self>) -> Self {
        let state = GasProbeCalleeState::load(runtime.root_view_storage_context())
            .await
            .expect("failed to load callee state");
        Self { state }
    }

    async fn instantiate(&mut self, _argument: Self::InstantiationArgument) {
        seed_state(&mut self.state).expect("failed to seed callee state");
    }

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
            GasProbeCalleeOperation::StateRead {
                payload_size,
                iteration,
            } => {
                let _bytes = self
                    .state
                    .bytes_by_size
                    .get(&read_key(payload_size, iteration))
                    .await
                    .expect("failed to read callee state")
                    .expect("missing seeded callee state");
                GasProbeResponse::Ok
            }
            GasProbeCalleeOperation::StateWrite {
                payload_size,
                iteration,
            } => {
                self.state
                    .bytes_by_size
                    .insert(
                        &write_key(payload_size, iteration),
                        vec![7; payload_size as usize],
                    )
                    .expect("failed to write callee state");
                GasProbeResponse::Ok
            }
        }
    }

    async fn execute_message(&mut self, _message: Self::Message) {}

    async fn store(mut self) {
        self.state
            .save()
            .await
            .expect("failed to save callee state");
    }
}

fn seed_state(state: &mut GasProbeCalleeState) -> Result<(), linera_sdk::views::ViewError> {
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
