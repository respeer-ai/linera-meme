use abi::meme::{MemeMessage, MemeOperation};
use abi::swap::router::{SwapMessage, SwapOperation};
use abi::swap::transaction::{Transaction, TransactionType};
use linera_sdk::linera_base_types::{Account, AccountOwner, Amount, ApplicationId, ChainId, CryptoHash, Timestamp};
use serde_json::json;

fn main() {
    let fixture = std::env::args().nth(1).unwrap_or_default();
    let bytes = match fixture.as_str() {
        "swap_update_pool_operation" => bcs::to_bytes(&build_swap_update_pool_operation()).unwrap(),
        "swap_update_pool_message" => bcs::to_bytes(&build_swap_update_pool_message()).unwrap(),
        "meme_transfer_operation" => bcs::to_bytes(&build_meme_transfer_operation()).unwrap(),
        "meme_transfer_message" => bcs::to_bytes(&build_meme_transfer_message()).unwrap(),
        _ => {
            eprintln!("unknown fixture: {fixture}");
            std::process::exit(1);
        }
    };
    println!("{}", json!({ "raw_bytes_hex": encode_bytes(&bytes) }));
}

fn build_swap_update_pool_operation() -> SwapOperation {
    SwapOperation::UpdatePool {
        token_0: sample_application_id(0x11),
        token_1: None,
        transaction: sample_transaction(),
        token_0_price: Amount::from_attos(7),
        token_1_price: Amount::from_attos(8),
        reserve_0: Amount::from_attos(9),
        reserve_1: Amount::from_attos(10),
    }
}

fn build_swap_update_pool_message() -> SwapMessage {
    SwapMessage::UpdatePool {
        token_0: sample_application_id(0x11),
        token_1: None,
        transaction: sample_transaction(),
        token_0_price: Amount::from_attos(7),
        token_1_price: Amount::from_attos(8),
        reserve_0: Amount::from_attos(9),
        reserve_1: Amount::from_attos(10),
    }
}

fn build_meme_transfer_operation() -> MemeOperation {
    MemeOperation::Transfer {
        to: Account::new(sample_chain_id(0x55), AccountOwner::from([0x66; 32])),
        amount: Amount::from_attos(13),
    }
}

fn build_meme_transfer_message() -> MemeMessage {
    MemeMessage::Transfer {
        from: Account::new(sample_chain_id(0x77), AccountOwner::from([0x88; 32])),
        to: Account::new(sample_chain_id(0x55), AccountOwner::from([0x66; 32])),
        amount: Amount::from_attos(13),
    }
}

fn sample_transaction() -> Transaction {
    Transaction {
        transaction_id: Some(12),
        transaction_type: TransactionType::AddLiquidity,
        from: Account::new(
            sample_chain_id(0x33),
            AccountOwner::from([0x44; 32]),
        ),
        amount_0_in: Some(Amount::from_attos(3)),
        amount_0_out: None,
        amount_1_in: Some(Amount::from_attos(4)),
        amount_1_out: None,
        liquidity: Some(Amount::from_attos(5)),
        created_at: Timestamp::from(99),
    }
}

fn sample_application_id(seed: u8) -> ApplicationId {
    ApplicationId::new(sample_hash(seed))
}

fn sample_chain_id(seed: u8) -> ChainId {
    ChainId(sample_hash(seed))
}

fn sample_hash(seed: u8) -> CryptoHash {
    CryptoHash::from([seed; 32])
}

fn encode_bytes(bytes: &[u8]) -> String {
    let mut output = String::with_capacity(bytes.len() * 2);
    for byte in bytes {
        output.push_str(&format!("{byte:02x}"));
    }
    output
}
