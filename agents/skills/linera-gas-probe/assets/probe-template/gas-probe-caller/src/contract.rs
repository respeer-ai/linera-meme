#![cfg_attr(target_arch = "wasm32", no_main)]

use gas_probe_abi::{
    decode_payload, encode_payload, sample_account_amount_payload, sample_amount,
    sample_bytes_payload, sample_pool_like_small_payload, GasProbeCalleeOperation,
    GasProbeCallerAbi, GasProbeCallerOperation, GasProbeResponse, PayloadKind,
};
use linera_sdk::{
    linera_base_types::WithContractAbi,
    views::{RootView, View},
    Contract, ContractRuntime,
};

mod state;

use state::GasProbeCallerState;

const READ_SLOT: u32 = 0;
const WRITE_SLOT: u32 = 1;

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
            GasProbeCallerOperation::BcsEncode { payload_kind } => {
                let _bytes = encode_payload(payload_kind);
                GasProbeResponse::Ok
            }
            GasProbeCallerOperation::BcsDecode {
                payload_kind,
                payload,
            } => {
                decode_payload(payload_kind, &payload);
                GasProbeResponse::Ok
            }
            GasProbeCallerOperation::RawStateRead { payload_size } => {
                let _bytes = self
                    .state
                    .bytes_by_size
                    .get(&raw_read_key(payload_size))
                    .await
                    .expect("failed to read caller raw state")
                    .expect("missing seeded caller raw state");
                GasProbeResponse::Ok
            }
            GasProbeCallerOperation::RawStateWrite { payload_size } => {
                self.state
                    .bytes_by_size
                    .insert(&raw_write_key(payload_size), vec![7; payload_size as usize])
                    .expect("failed to write caller raw state");
                GasProbeResponse::Ok
            }
            GasProbeCallerOperation::TypedStateRead { payload_kind } => {
                read_typed_state(&self.state, payload_kind).await;
                GasProbeResponse::Ok
            }
            GasProbeCallerOperation::TypedStateWrite { payload_kind } => {
                write_typed_state(&mut self.state, payload_kind)
                    .expect("failed to write caller typed state");
                GasProbeResponse::Ok
            }
            GasProbeCallerOperation::GenericStateBcsEncodeWrite { payload_kind } => {
                let payload = encode_payload(payload_kind);
                self.state
                    .bytes_by_size
                    .insert(&generic_write_key(payload_kind), payload)
                    .expect("failed to write caller generic state");
                GasProbeResponse::Ok
            }
            GasProbeCallerOperation::GenericStateReadBcsDecode { payload_kind } => {
                let bytes = self
                    .state
                    .bytes_by_size
                    .get(&generic_read_key(payload_kind))
                    .await
                    .expect("failed to read caller generic state")
                    .expect("missing seeded caller generic state");
                decode_payload(payload_kind, &bytes);
                GasProbeResponse::Ok
            }
            GasProbeCallerOperation::CallApplicationNoop { callee } => {
                let _response =
                    self.runtime
                        .call_application(true, callee, &GasProbeCalleeOperation::Noop);
                GasProbeResponse::Ok
            }
            GasProbeCallerOperation::CallApplicationEcho {
                callee,
                payload_size,
            } => {
                let _response = self.runtime.call_application(
                    true,
                    callee,
                    &GasProbeCalleeOperation::EchoBytes {
                        payload: vec![7; payload_size as usize],
                    },
                );
                GasProbeResponse::Ok
            }
            GasProbeCallerOperation::CallApplicationDecode {
                callee,
                payload_kind,
            } => {
                let payload = encode_payload(payload_kind);
                let _response = self.runtime.call_application(
                    true,
                    callee,
                    &GasProbeCalleeOperation::DecodeBytes {
                        payload_kind,
                        payload,
                    },
                );
                GasProbeResponse::Ok
            }
            GasProbeCallerOperation::CallApplicationGenericStateBcsEncodeWrite {
                callee,
                payload_kind,
            } => {
                let payload = encode_payload(payload_kind);
                let _response = self.runtime.call_application(
                    true,
                    callee,
                    &GasProbeCalleeOperation::GenericStateWriteBytes {
                        payload_kind,
                        payload,
                    },
                );
                GasProbeResponse::Ok
            }
            GasProbeCallerOperation::CallApplicationGenericStateReadBcsDecode {
                callee,
                payload_kind,
            } => {
                let _response = self.runtime.call_application(
                    true,
                    callee,
                    &GasProbeCalleeOperation::GenericStateReadBytes { payload_kind },
                );
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
    for payload_kind in generic_payload_kinds() {
        seed_typed_state(state, payload_kind)?;
        state.bytes_by_size.insert(
            &generic_read_key(payload_kind),
            encode_payload(payload_kind),
        )?;
    }

    for size in [32, 512, 2048] {
        state
            .bytes_by_size
            .insert(&raw_read_key(size), vec![7; size as usize])?;
    }
    Ok(())
}

async fn read_typed_state(state: &GasProbeCallerState, payload_kind: PayloadKind) {
    match payload_kind {
        PayloadKind::Amount => {
            let _value = state
                .amounts
                .get(&typed_read_key(payload_kind))
                .await
                .expect("failed to read caller typed amount")
                .expect("missing seeded caller typed amount");
        }
        PayloadKind::AccountAmount => {
            let _value = state
                .account_amounts
                .get(&typed_read_key(payload_kind))
                .await
                .expect("failed to read caller typed account amount")
                .expect("missing seeded caller typed account amount");
        }
        PayloadKind::PoolLikeSmall => {
            let _value = state
                .pool_like_smalls
                .get(&typed_read_key(payload_kind))
                .await
                .expect("failed to read caller typed pool-like payload")
                .expect("missing seeded caller typed pool-like payload");
        }
        PayloadKind::Bytes512 | PayloadKind::Bytes2048 => {
            let _value = state
                .bytes_by_size
                .get(&typed_read_key(payload_kind))
                .await
                .expect("failed to read caller typed bytes")
                .expect("missing seeded caller typed bytes");
        }
        PayloadKind::Account | PayloadKind::Bytes32 | PayloadKind::Bytes128 => {
            panic!("unsupported typed state payload kind")
        }
    }
}

fn seed_typed_state(
    state: &mut GasProbeCallerState,
    payload_kind: PayloadKind,
) -> Result<(), linera_sdk::views::ViewError> {
    insert_typed_state(state, payload_kind, typed_read_key(payload_kind))
}

fn write_typed_state(
    state: &mut GasProbeCallerState,
    payload_kind: PayloadKind,
) -> Result<(), linera_sdk::views::ViewError> {
    insert_typed_state(state, payload_kind, typed_write_key(payload_kind))
}

fn insert_typed_state(
    state: &mut GasProbeCallerState,
    payload_kind: PayloadKind,
    key: u32,
) -> Result<(), linera_sdk::views::ViewError> {
    match payload_kind {
        PayloadKind::Amount => state.amounts.insert(&key, sample_amount()),
        PayloadKind::AccountAmount => state
            .account_amounts
            .insert(&key, sample_account_amount_payload()),
        PayloadKind::PoolLikeSmall => state
            .pool_like_smalls
            .insert(&key, sample_pool_like_small_payload()),
        PayloadKind::Bytes512 | PayloadKind::Bytes2048 => state
            .bytes_by_size
            .insert(&key, sample_bytes_payload(payload_kind)),
        PayloadKind::Account | PayloadKind::Bytes32 | PayloadKind::Bytes128 => {
            panic!("unsupported typed state payload kind")
        }
    }
}

fn generic_payload_kinds() -> [PayloadKind; 5] {
    [
        PayloadKind::Amount,
        PayloadKind::AccountAmount,
        PayloadKind::PoolLikeSmall,
        PayloadKind::Bytes512,
        PayloadKind::Bytes2048,
    ]
}

fn typed_read_key(payload_kind: PayloadKind) -> u32 {
    2_000_000 + payload_kind_index(payload_kind) * 100 + READ_SLOT
}

fn typed_write_key(payload_kind: PayloadKind) -> u32 {
    2_000_000 + payload_kind_index(payload_kind) * 100 + WRITE_SLOT
}

fn raw_read_key(payload_size: u32) -> u32 {
    payload_size * 10_000 + READ_SLOT
}

fn raw_write_key(payload_size: u32) -> u32 {
    payload_size * 10_000 + WRITE_SLOT
}

fn generic_read_key(payload_kind: PayloadKind) -> u32 {
    1_000_000 + payload_kind_index(payload_kind) * 100 + READ_SLOT
}

fn generic_write_key(payload_kind: PayloadKind) -> u32 {
    1_000_000 + payload_kind_index(payload_kind) * 100 + WRITE_SLOT
}

fn payload_kind_index(payload_kind: PayloadKind) -> u32 {
    match payload_kind {
        PayloadKind::Amount => 1,
        PayloadKind::Account => 2,
        PayloadKind::AccountAmount => 3,
        PayloadKind::PoolLikeSmall => 4,
        PayloadKind::Bytes32 => 5,
        PayloadKind::Bytes128 => 6,
        PayloadKind::Bytes512 => 7,
        PayloadKind::Bytes2048 => 8,
    }
}
