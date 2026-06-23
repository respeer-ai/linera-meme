use gas_probe_abi::{encode_payload, GasProbeCalleeAbi, GasProbeCallerOperation, PayloadKind};
use linera_sdk::linera_base_types::ApplicationId;
use std::{env, str::FromStr};

fn main() {
    let args: Vec<String> = env::args().collect();
    if args.len() < 2 {
        panic!("usage: gas-probe-opgen <case> [args]");
    }
    let op = match args[1].as_str() {
        "noop" => GasProbeCallerOperation::Noop,
        "bcs-encode" => GasProbeCallerOperation::BcsEncode {
            payload_kind: parse_kind(&args[2]),
            iterations: parse_u32(&args[3]),
        },
        "bcs-decode" => {
            let payload_kind = parse_kind(&args[2]);
            GasProbeCallerOperation::BcsDecode {
                payload_kind,
                payload: encode_payload(payload_kind),
                iterations: parse_u32(&args[3]),
            }
        }
        "direct-state-read" => GasProbeCallerOperation::DirectStateRead {
            payload_size: parse_u32(&args[2]),
            iterations: parse_u32(&args[3]),
        },
        "direct-state-write" => GasProbeCallerOperation::DirectStateWrite {
            payload_size: parse_u32(&args[2]),
            iterations: parse_u32(&args[3]),
        },
        "call-noop" => GasProbeCallerOperation::CallApplicationNoop {
            callee: parse_app(&args[2]),
            iterations: parse_u32(&args[3]),
        },
        "call-echo" => GasProbeCallerOperation::CallApplicationEcho {
            callee: parse_app(&args[2]),
            payload_size: parse_u32(&args[3]),
            iterations: parse_u32(&args[4]),
        },
        "call-decode" => GasProbeCallerOperation::CallApplicationDecode {
            callee: parse_app(&args[2]),
            payload_kind: parse_kind(&args[3]),
            iterations: parse_u32(&args[4]),
        },
        "call-state-read" => GasProbeCallerOperation::CallApplicationStateRead {
            callee: parse_app(&args[2]),
            payload_size: parse_u32(&args[3]),
            iterations: parse_u32(&args[4]),
        },
        "call-state-write" => GasProbeCallerOperation::CallApplicationStateWrite {
            callee: parse_app(&args[2]),
            payload_size: parse_u32(&args[3]),
            iterations: parse_u32(&args[4]),
        },
        other => panic!("unknown case {other}"),
    };
    let bytes = bcs::to_bytes(&op).unwrap();
    println!("{}", hex::encode(bytes));
}

fn parse_u32(value: &str) -> u32 {
    value.parse().unwrap()
}

fn parse_app(value: &str) -> ApplicationId<GasProbeCalleeAbi> {
    ApplicationId::from_str(value)
        .unwrap()
        .with_abi::<GasProbeCalleeAbi>()
}

fn parse_kind(value: &str) -> PayloadKind {
    match value {
        "amount" => PayloadKind::Amount,
        "account" => PayloadKind::Account,
        "account-amount" => PayloadKind::AccountAmount,
        "pool-like-small" => PayloadKind::PoolLikeSmall,
        "bytes32" => PayloadKind::Bytes32,
        "bytes128" => PayloadKind::Bytes128,
        "bytes512" => PayloadKind::Bytes512,
        "bytes2048" => PayloadKind::Bytes2048,
        other => panic!("unknown payload kind {other}"),
    }
}
