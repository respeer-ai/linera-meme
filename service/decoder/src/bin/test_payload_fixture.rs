use abi::ams::AmsMessage;
use abi::blob_gateway::{BlobData, BlobDataType, BlobGatewayMessage};
use abi::meme::{MemeMessage, MemeOperation};
use abi::proxy::ProxyMessage;
use abi::store_type::StoreType;
use abi::swap::pool::{ClaimTransferReceipt, FundRequest, FundType, PoolMessage, PoolOperation};
use abi::swap::router::{SwapMessage, SwapOperation};
use abi::swap::transaction::{Transaction, TransactionType};
use linera_sdk::linera_base_types::{
    Account, AccountOwner, Amount, ApplicationId, ChainId, CryptoHash, Timestamp,
};
use serde_json::json;

fn main() {
    let fixture = std::env::args().nth(1).unwrap_or_default();
    let bytes = match fixture.as_str() {
        "swap_update_pool_operation" => bcs::to_bytes(&build_swap_update_pool_operation()).unwrap(),
        "swap_update_pool_message" => bcs::to_bytes(&build_swap_update_pool_message()).unwrap(),
        "pool_swap_operation" => bcs::to_bytes(&build_pool_swap_operation()).unwrap(),
        "pool_fund_result_message" => bcs::to_bytes(&build_pool_fund_result_message()).unwrap(),
        "pool_claim_transfer_receipt_message" => {
            bcs::to_bytes(&build_pool_claim_transfer_receipt_message()).unwrap()
        }
        "pool_new_transaction_message" => {
            bcs::to_bytes(&build_pool_new_transaction_message()).unwrap()
        }
        "meme_transfer_operation" => bcs::to_bytes(&build_meme_transfer_operation()).unwrap(),
        "meme_transfer_message" => bcs::to_bytes(&build_meme_transfer_message()).unwrap(),
        "proxy_register_miner_message" => {
            bcs::to_bytes(&build_proxy_register_miner_message()).unwrap()
        }
        "ams_add_application_type_message" => {
            bcs::to_bytes(&build_ams_add_application_type_message()).unwrap()
        }
        "blob_gateway_register_message" => {
            bcs::to_bytes(&build_blob_gateway_register_message()).unwrap()
        }
        _ => {
            eprintln!("unknown fixture: {fixture}");
            std::process::exit(1);
        }
    };
    println!("{}", json!({ "raw_bytes_hex": encode_bytes(&bytes) }));
}

fn build_pool_swap_operation() -> PoolOperation {
    PoolOperation::Swap {
        amount_0_in: Some(Amount::from_attos(5)),
        amount_1_in: None,
        amount_0_out_min: None,
        amount_1_out_min: Some(Amount::from_attos(7)),
        to: None,
        block_timestamp: None,
    }
}

fn build_pool_fund_result_message() -> PoolMessage {
    let request = sample_fund_request();
    PoolMessage::FundResult {
        prev: None,
        request,
        next: None,
        result: Ok(()),
    }
}

fn build_pool_claim_transfer_receipt_message() -> PoolMessage {
    PoolMessage::ClaimTransferReceipt {
        receipt: ClaimTransferReceipt {
            owner: sample_account(0x33, 0x44),
            token: sample_application_id(0x11),
            amount: Amount::from_attos(13),
            result: Ok(()),
        },
    }
}

fn build_pool_new_transaction_message() -> PoolMessage {
    PoolMessage::NewTransaction {
        transaction: sample_transaction(),
    }
}

fn sample_fund_request() -> FundRequest {
    FundRequest {
        from: sample_account(0x33, 0x44),
        token: Some(sample_application_id(0x11)),
        amount_in: Amount::from_attos(13),
        amount_out_min: Some(Amount::from_attos(7)),
        counterparty_token: None,
        counterparty_amount_in: None,
        counterparty_amount_out_min: Some(Amount::from_attos(5)),
        to: Some(sample_account(0x55, 0x66)),
        block_timestamp: Some(Timestamp::from(99)),
        fund_type: FundType::Swap,
    }
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

fn build_proxy_register_miner_message() -> ProxyMessage {
    ProxyMessage::RegisterMiner {
        owner: Account::new(sample_chain_id(0x11), AccountOwner::from([0x22; 32])),
    }
}

fn build_ams_add_application_type_message() -> AmsMessage {
    AmsMessage::AddApplicationType {
        owner: Account::new(sample_chain_id(0x11), AccountOwner::from([0x22; 32])),
        application_type: "DeFi".to_owned(),
    }
}

fn build_blob_gateway_register_message() -> BlobGatewayMessage {
    BlobGatewayMessage::Register {
        blob_data: BlobData {
            store_type: StoreType::Ipfs,
            data_type: BlobDataType::Html,
            blob_hash: sample_hash(0x22),
            creator: Account::new(sample_chain_id(0x11), AccountOwner::from([0x33; 32])),
            created_at: Timestamp::from(99),
        },
    }
}

fn sample_account(chain_seed: u8, owner_seed: u8) -> Account {
    Account::new(
        sample_chain_id(chain_seed),
        AccountOwner::from([owner_seed; 32]),
    )
}

fn sample_transaction() -> Transaction {
    Transaction {
        transaction_id: Some(12),
        transaction_type: TransactionType::AddLiquidity,
        from: Account::new(sample_chain_id(0x33), AccountOwner::from([0x44; 32])),
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
