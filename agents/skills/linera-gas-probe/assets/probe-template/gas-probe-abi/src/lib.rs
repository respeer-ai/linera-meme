use linera_sdk::linera_base_types::{
    Account, AccountOwner, Amount, ApplicationId, ChainId, ContractAbi, CryptoHash, ServiceAbi,
};
use serde::{Deserialize, Serialize};

pub struct GasProbeCallerAbi;

impl ContractAbi for GasProbeCallerAbi {
    type Operation = GasProbeCallerOperation;
    type Response = GasProbeResponse;
}

impl ServiceAbi for GasProbeCallerAbi {
    type Query = Vec<u8>;
    type QueryResponse = Vec<u8>;
}

pub struct GasProbeCalleeAbi;

impl ContractAbi for GasProbeCalleeAbi {
    type Operation = GasProbeCalleeOperation;
    type Response = GasProbeResponse;
}

impl ServiceAbi for GasProbeCalleeAbi {
    type Query = Vec<u8>;
    type QueryResponse = Vec<u8>;
}

#[derive(Clone, Debug, Deserialize, Serialize)]
pub enum GasProbeCallerOperation {
    Noop,
    BcsEncode {
        payload_kind: PayloadKind,
    },
    BcsDecode {
        payload_kind: PayloadKind,
        payload: Vec<u8>,
    },
    RawStateRead {
        payload_size: u32,
    },
    RawStateWrite {
        payload_size: u32,
    },
    TypedStateRead {
        payload_kind: PayloadKind,
    },
    TypedStateWrite {
        payload_kind: PayloadKind,
    },
    GenericStateBcsEncodeWrite {
        payload_kind: PayloadKind,
    },
    GenericStateReadBcsDecode {
        payload_kind: PayloadKind,
    },
    CallApplicationNoop {
        callee: ApplicationId<GasProbeCalleeAbi>,
    },
    CallApplicationEcho {
        callee: ApplicationId<GasProbeCalleeAbi>,
        payload_size: u32,
    },
    CallApplicationDecode {
        callee: ApplicationId<GasProbeCalleeAbi>,
        payload_kind: PayloadKind,
    },
    CallApplicationGenericStateBcsEncodeWrite {
        callee: ApplicationId<GasProbeCalleeAbi>,
        payload_kind: PayloadKind,
    },
    CallApplicationGenericStateReadBcsDecode {
        callee: ApplicationId<GasProbeCalleeAbi>,
        payload_kind: PayloadKind,
    },
}

#[derive(Clone, Debug, Deserialize, Serialize)]
pub enum GasProbeCalleeOperation {
    Noop,
    EchoBytes {
        payload: Vec<u8>,
    },
    DecodeBytes {
        payload_kind: PayloadKind,
        payload: Vec<u8>,
    },
    GenericStateReadBytes {
        payload_kind: PayloadKind,
    },
    GenericStateWriteBytes {
        payload_kind: PayloadKind,
        payload: Vec<u8>,
    },
}

#[derive(Clone, Copy, Debug, Deserialize, Serialize)]
pub enum PayloadKind {
    Amount,
    Account,
    AccountAmount,
    PoolLikeSmall,
    Bytes32,
    Bytes128,
    Bytes512,
    Bytes2048,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
pub struct AccountAmountPayload {
    pub account: Account,
    pub amount: Amount,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
pub struct PoolLikeSmallPayload {
    pub token_0: ApplicationId,
    pub token_1: Option<ApplicationId>,
    pub chain_id: ChainId,
    pub reserve_0: Amount,
    pub reserve_1: Amount,
    pub total_supply: Amount,
    pub fee_to: Account,
    pub fee_to_setter: Account,
}

#[derive(Clone, Debug, Deserialize, Serialize, Default)]
pub enum GasProbeResponse {
    #[default]
    Ok,
    Bytes(Vec<u8>),
}

pub fn encode_payload(kind: PayloadKind) -> Vec<u8> {
    match kind {
        PayloadKind::Amount => bcs::to_bytes(&sample_amount()).unwrap(),
        PayloadKind::Account => bcs::to_bytes(&sample_account()).unwrap(),
        PayloadKind::AccountAmount => bcs::to_bytes(&sample_account_amount_payload()).unwrap(),
        PayloadKind::PoolLikeSmall => bcs::to_bytes(&sample_pool_like_small_payload()).unwrap(),
        PayloadKind::Bytes32
        | PayloadKind::Bytes128
        | PayloadKind::Bytes512
        | PayloadKind::Bytes2048 => bcs::to_bytes(&sample_bytes_payload(kind)).unwrap(),
    }
}

pub fn decode_payload(kind: PayloadKind, payload: &[u8]) {
    match kind {
        PayloadKind::Amount => {
            let _decoded: Amount = bcs::from_bytes(payload).unwrap();
        }
        PayloadKind::Account => {
            let _decoded: Account = bcs::from_bytes(payload).unwrap();
        }
        PayloadKind::AccountAmount => {
            let _decoded: AccountAmountPayload = bcs::from_bytes(payload).unwrap();
        }
        PayloadKind::PoolLikeSmall => {
            let _decoded: PoolLikeSmallPayload = bcs::from_bytes(payload).unwrap();
        }
        PayloadKind::Bytes32
        | PayloadKind::Bytes128
        | PayloadKind::Bytes512
        | PayloadKind::Bytes2048 => {
            let _decoded: Vec<u8> = bcs::from_bytes(payload).unwrap();
        }
    }
}

pub fn sample_amount() -> Amount {
    Amount::from_tokens(123_456)
}

pub fn sample_account_amount_payload() -> AccountAmountPayload {
    AccountAmountPayload {
        account: sample_account(),
        amount: Amount::from_tokens(42),
    }
}

pub fn sample_pool_like_small_payload() -> PoolLikeSmallPayload {
    PoolLikeSmallPayload {
        token_0: sample_application_id(1),
        token_1: Some(sample_application_id(2)),
        chain_id: sample_chain_id(7),
        reserve_0: Amount::from_tokens(1_000_000),
        reserve_1: Amount::from_tokens(2_000_000),
        total_supply: Amount::from_tokens(3_000_000),
        fee_to: sample_account(),
        fee_to_setter: sample_account(),
    }
}

pub fn sample_bytes_payload(kind: PayloadKind) -> Vec<u8> {
    match kind {
        PayloadKind::Bytes32 => vec![7u8; 32],
        PayloadKind::Bytes128 => vec![7u8; 128],
        PayloadKind::Bytes512 => vec![7u8; 512],
        PayloadKind::Bytes2048 => vec![7u8; 2048],
        _ => panic!("payload kind is not bytes"),
    }
}

fn sample_account() -> Account {
    Account {
        chain_id: sample_chain_id(9),
        owner: AccountOwner::CHAIN,
    }
}

fn sample_application_id(seed: u8) -> ApplicationId {
    ApplicationId::new(CryptoHash::try_from(&[seed; 32][..]).unwrap())
}

fn sample_chain_id(seed: u8) -> ChainId {
    ChainId(CryptoHash::try_from(&[seed; 32][..]).unwrap())
}
