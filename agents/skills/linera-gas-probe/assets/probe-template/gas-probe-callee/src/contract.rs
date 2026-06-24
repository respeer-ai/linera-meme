#![cfg_attr(target_arch = "wasm32", no_main)]

use gas_probe_abi::{decode_payload, GasProbeCalleeAbi, GasProbeCalleeOperation, GasProbeResponse};
use linera_sdk::{
    linera_base_types::WithContractAbi,
    views::{RootView, View},
    Contract, ContractRuntime,
};

mod state;

use state::GasProbeCalleeState;

const READ_SLOT: u32 = 0;
const WRITE_SLOT: u32 = 1;

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
            GasProbeCalleeOperation::GenericStateReadBytes { payload_kind } => {
                let bytes = self
                    .state
                    .bytes_by_size
                    .get(&generic_read_key(payload_kind))
                    .await
                    .expect("failed to read callee generic state")
                    .expect("missing seeded callee generic state");
                decode_payload(payload_kind, &bytes);
                GasProbeResponse::Ok
            }
            GasProbeCalleeOperation::GenericStateWriteBytes {
                payload_kind,
                payload,
            } => {
                self.state
                    .bytes_by_size
                    .insert(&generic_write_key(payload_kind), payload)
                    .expect("failed to write callee generic state");
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
    for kind in [
        gas_probe_abi::PayloadKind::Amount,
        gas_probe_abi::PayloadKind::AccountAmount,
        gas_probe_abi::PayloadKind::PoolLikeSmall,
        gas_probe_abi::PayloadKind::Bytes512,
        gas_probe_abi::PayloadKind::Bytes2048,
    ] {
        state
            .bytes_by_size
            .insert(&generic_read_key(kind), gas_probe_abi::encode_payload(kind))?;
    }
    Ok(())
}

fn generic_read_key(payload_kind: gas_probe_abi::PayloadKind) -> u32 {
    1_000_000 + payload_kind_index(payload_kind) * 100 + READ_SLOT
}

fn generic_write_key(payload_kind: gas_probe_abi::PayloadKind) -> u32 {
    1_000_000 + payload_kind_index(payload_kind) * 100 + WRITE_SLOT
}

fn payload_kind_index(payload_kind: gas_probe_abi::PayloadKind) -> u32 {
    match payload_kind {
        gas_probe_abi::PayloadKind::Amount => 1,
        gas_probe_abi::PayloadKind::Account => 2,
        gas_probe_abi::PayloadKind::AccountAmount => 3,
        gas_probe_abi::PayloadKind::PoolLikeSmall => 4,
        gas_probe_abi::PayloadKind::Bytes32 => 5,
        gas_probe_abi::PayloadKind::Bytes128 => 6,
        gas_probe_abi::PayloadKind::Bytes512 => 7,
        gas_probe_abi::PayloadKind::Bytes2048 => 8,
    }
}
