use abi::ams::{AmsMessage, AmsOperation};
use abi::blob_gateway::{BlobGatewayMessage, BlobGatewayOperation};
use abi::meme::{MemeMessage, MemeOperation};
use abi::proxy::{ProxyMessage, ProxyOperation};
use abi::swap::pool::{BootstrapPolicy, PoolMessage, PoolOperation};
use abi::swap::router::{SwapMessage, SwapOperation};
use abi::swap::transaction::{Transaction, TransactionType};
use linera_sdk::linera_base_types::{Account, AccountOwner, Amount, Timestamp};
use serde::Deserialize;
use serde_json::{json, Value};
use std::io::{self, Read};

#[derive(Deserialize)]
struct DecodeRequest {
    app_type: String,
    payload_kind: String,
    application_id: String,
    raw_bytes_hex: String,
}

fn main() {
    let mut input = String::new();
    if io::stdin().read_to_string(&mut input).is_err() {
        eprintln!("failed to read stdin");
        std::process::exit(1);
    }
    let input = input.trim().to_owned();

    // Batch mode: JSON array
    if input.starts_with('[') {
        let requests: Vec<DecodeRequest> = match serde_json::from_str(&input) {
            Ok(r) => r,
            Err(e) => {
                eprintln!("failed to parse batch request: {e}");
                std::process::exit(1);
            }
        };
        let results: Vec<Value> = requests.iter().map(decode_single).collect();
        println!("{}", serde_json::to_string(&results).unwrap());
        return;
    }

    // Single mode: JSON object (backwards-compatible)
    let request: DecodeRequest = match serde_json::from_str(&input) {
        Ok(r) => r,
        Err(e) => {
            eprintln!("failed to parse request: {e}");
            std::process::exit(1);
        }
    };
    match decode_single(&request) {
        Value::Object(map) if map.get("status").and_then(|v| v.as_str()) == Some("error") => {
            eprintln!("{}", map["error"].as_str().unwrap_or("decode failed"));
            std::process::exit(1);
        }
        result => {
            println!("{}", serde_json::to_string(&result).unwrap());
        }
    }
}

fn decode_single(request: &DecodeRequest) -> Value {
    let raw_bytes = match decode_hex(&request.raw_bytes_hex) {
        Ok(b) => b,
        Err(e) => return json!({"status": "error", "error": format!("invalid hex: {e}")}),
    };
    let result = match (request.app_type.as_str(), request.payload_kind.as_str()) {
        ("pool", "operation") => decode_pool_operation(&request.application_id, &raw_bytes),
        ("pool", "message") => decode_pool_message(&request.application_id, &raw_bytes),
        ("pool", "event") => Err(anyhow::anyhow!(
            "pool:event canonical decoding is not implemented"
        )),
        ("swap", "operation") => decode_swap_operation(&request.application_id, &raw_bytes),
        ("swap", "message") => decode_swap_message(&request.application_id, &raw_bytes),
        ("meme", "operation") => decode_meme_operation(&request.application_id, &raw_bytes),
        ("meme", "message") => decode_meme_message(&request.application_id, &raw_bytes),
        ("proxy", "operation") => decode_proxy_operation(&request.application_id, &raw_bytes),
        ("proxy", "message") => decode_proxy_message(&request.application_id, &raw_bytes),
        ("ams", "operation") => decode_ams_operation(&request.application_id, &raw_bytes),
        ("ams", "message") => decode_ams_message(&request.application_id, &raw_bytes),
        ("blob-gateway", "operation") => {
            decode_blob_gateway_operation(&request.application_id, &raw_bytes)
        }
        ("blob-gateway", "message") => {
            decode_blob_gateway_message(&request.application_id, &raw_bytes)
        }
        _ => Err(anyhow::anyhow!(
            "unsupported canonical decoder target: {}:{}",
            request.app_type,
            request.payload_kind
        )),
    };
    match result {
        Ok(payload) => {
            let mut output = json!({"status": "ok"});
            if let Value::Object(ref mut map) = output {
                if let Value::Object(payload_map) = payload {
                    map.extend(payload_map);
                }
            }
            output
        }
        Err(e) => json!({"status": "error", "error": e.to_string()}),
    }
}

fn decode_pool_operation(application_id: &str, raw_bytes: &[u8]) -> anyhow::Result<Value> {
    let operation = bcs::from_bytes::<PoolOperation>(raw_bytes)?;
    let (payload_type, decoded_payload_json) = match operation {
        PoolOperation::SetFeeTo { account } => (
            "set_fee_to",
            json!({
                "operation_type": "set_fee_to",
                "application_id": application_id,
                "account": encode_account(account),
            }),
        ),
        PoolOperation::SetFeeToSetter { account } => (
            "set_fee_to_setter",
            json!({
                "operation_type": "set_fee_to_setter",
                "application_id": application_id,
                "account": encode_account(account),
            }),
        ),
        PoolOperation::InitializeLiquidity {
            amount_0_in,
            amount_1_in,
            to,
            block_timestamp,
        } => (
            "initialize_liquidity",
            json!({
                "operation_type": "initialize_liquidity",
                "application_id": application_id,
                "amount_0_in": encode_amount(amount_0_in),
                "amount_1_in": encode_amount(amount_1_in),
                "to": encode_option_account(to),
                "block_timestamp_micros": encode_option_timestamp(block_timestamp),
            }),
        ),
        PoolOperation::AddLiquidity {
            amount_0_in,
            amount_1_in,
            amount_0_out_min,
            amount_1_out_min,
            to,
            block_timestamp,
        } => (
            "add_liquidity",
            json!({
                "operation_type": "add_liquidity",
                "application_id": application_id,
                "amount_0_in": encode_amount(amount_0_in),
                "amount_1_in": encode_amount(amount_1_in),
                "amount_0_out_min": encode_option_amount(amount_0_out_min),
                "amount_1_out_min": encode_option_amount(amount_1_out_min),
                "to": encode_option_account(to),
                "block_timestamp_micros": encode_option_timestamp(block_timestamp),
            }),
        ),
        PoolOperation::RemoveLiquidity {
            liquidity,
            amount_0_out_min,
            amount_1_out_min,
            to,
            block_timestamp,
        } => (
            "remove_liquidity",
            json!({
                "operation_type": "remove_liquidity",
                "application_id": application_id,
                "liquidity": encode_amount(liquidity),
                "amount_0_out_min": encode_option_amount(amount_0_out_min),
                "amount_1_out_min": encode_option_amount(amount_1_out_min),
                "to": encode_option_account(to),
                "block_timestamp_micros": encode_option_timestamp(block_timestamp),
            }),
        ),
        PoolOperation::Swap {
            amount_0_in,
            amount_1_in,
            amount_0_out_min,
            amount_1_out_min,
            to,
            block_timestamp,
        } => (
            "swap",
            json!({
                "operation_type": "swap",
                "application_id": application_id,
                "amount_0_in": encode_option_amount(amount_0_in),
                "amount_1_in": encode_option_amount(amount_1_in),
                "amount_0_out_min": encode_option_amount(amount_0_out_min),
                "amount_1_out_min": encode_option_amount(amount_1_out_min),
                "to": encode_option_account(to),
                "block_timestamp_micros": encode_option_timestamp(block_timestamp),
            }),
        ),
    };
    Ok(json!({
        "payload_type": payload_type,
        "decoder_version": "pool-operation-rust-v1",
        "decoded_payload_json": decoded_payload_json,
    }))
}

fn decode_pool_message(application_id: &str, raw_bytes: &[u8]) -> anyhow::Result<Value> {
    let message = bcs::from_bytes::<PoolMessage>(raw_bytes)?;
    let (payload_type, decoded_payload_json) = match message {
        PoolMessage::RequestFund {
            token,
            transfer_id,
            amount,
        } => (
            "request_fund",
            json!({
                "message_type": "request_fund",
                "application_id": application_id,
                "token": token.to_string(),
                "transfer_id": transfer_id,
                "amount": encode_amount(amount),
            }),
        ),
        PoolMessage::FundSuccess { transfer_id } => (
            "fund_success",
            json!({
                "message_type": "fund_success",
                "application_id": application_id,
                "transfer_id": transfer_id,
            }),
        ),
        PoolMessage::FundFail { transfer_id, error } => (
            "fund_fail",
            json!({
                "message_type": "fund_fail",
                "application_id": application_id,
                "transfer_id": transfer_id,
                "error": error,
            }),
        ),
        PoolMessage::Swap {
            origin,
            amount_0_in,
            amount_1_in,
            amount_0_out_min,
            amount_1_out_min,
            to,
            block_timestamp,
        } => (
            "swap",
            json!({
                "message_type": "swap",
                "application_id": application_id,
                "origin": encode_account(origin),
                "amount_0_in": encode_option_amount(amount_0_in),
                "amount_1_in": encode_option_amount(amount_1_in),
                "amount_0_out_min": encode_option_amount(amount_0_out_min),
                "amount_1_out_min": encode_option_amount(amount_1_out_min),
                "to": encode_option_account(to),
                "block_timestamp_micros": encode_option_timestamp(block_timestamp),
            }),
        ),
        PoolMessage::AddLiquidity {
            origin,
            amount_0_in,
            amount_1_in,
            amount_0_out_min,
            amount_1_out_min,
            to,
            block_timestamp,
        } => (
            "add_liquidity",
            json!({
                "message_type": "add_liquidity",
                "application_id": application_id,
                "origin": encode_account(origin),
                "amount_0_in": encode_amount(amount_0_in),
                "amount_1_in": encode_amount(amount_1_in),
                "amount_0_out_min": encode_option_amount(amount_0_out_min),
                "amount_1_out_min": encode_option_amount(amount_1_out_min),
                "to": encode_option_account(to),
                "block_timestamp_micros": encode_option_timestamp(block_timestamp),
            }),
        ),
        PoolMessage::InitializeLiquidity {
            origin,
            amount_0_in,
            amount_1_in,
            to,
            block_timestamp,
        } => (
            "initialize_liquidity",
            json!({
                "message_type": "initialize_liquidity",
                "application_id": application_id,
                "origin": encode_account(origin),
                "amount_0_in": encode_amount(amount_0_in),
                "amount_1_in": encode_amount(amount_1_in),
                "to": encode_option_account(to),
                "block_timestamp_micros": encode_option_timestamp(block_timestamp),
            }),
        ),
        PoolMessage::RemoveLiquidity {
            origin,
            liquidity,
            amount_0_out_min,
            amount_1_out_min,
            to,
            block_timestamp,
        } => (
            "remove_liquidity",
            json!({
                "message_type": "remove_liquidity",
                "application_id": application_id,
                "origin": encode_account(origin),
                "liquidity": encode_amount(liquidity),
                "amount_0_out_min": encode_option_amount(amount_0_out_min),
                "amount_1_out_min": encode_option_amount(amount_1_out_min),
                "to": encode_option_account(to),
                "block_timestamp_micros": encode_option_timestamp(block_timestamp),
            }),
        ),
        PoolMessage::SetFeeTo { operator, account } => (
            "set_fee_to",
            json!({
                "message_type": "set_fee_to",
                "application_id": application_id,
                "operator": encode_account(operator),
                "account": encode_account(account),
            }),
        ),
        PoolMessage::SetFeeToSetter { operator, account } => (
            "set_fee_to_setter",
            json!({
                "message_type": "set_fee_to_setter",
                "application_id": application_id,
                "operator": encode_account(operator),
                "account": encode_account(account),
            }),
        ),
        PoolMessage::NewTransaction { transaction } => (
            "new_transaction",
            json!({
                "message_type": "new_transaction",
                "application_id": application_id,
                "transaction": encode_transaction(transaction),
            }),
        ),
    };
    Ok(json!({
        "payload_type": payload_type,
        "decoder_version": "pool-message-rust-v1",
        "decoded_payload_json": decoded_payload_json,
    }))
}

fn decode_proxy_operation(application_id: &str, raw_bytes: &[u8]) -> anyhow::Result<Value> {
    let operation = bcs::from_bytes::<ProxyOperation>(raw_bytes)?;
    let payload_type = match operation {
        ProxyOperation::RegisterMiner => "register_miner",
        ProxyOperation::DeregisterMiner => "deregister_miner",
        ProxyOperation::ProposeAddGenesisMiner { .. } => "propose_add_genesis_miner",
        ProxyOperation::ApproveAddGenesisMiner { .. } => "approve_add_genesis_miner",
        ProxyOperation::ProposeRemoveGenesisMiner { .. } => "propose_remove_genesis_miner",
        ProxyOperation::ApproveRemoveGenesisMiner { .. } => "approve_remove_genesis_miner",
        ProxyOperation::CreateMeme { .. } => "create_meme",
        ProxyOperation::ProposeAddOperator { .. } => "propose_add_operator",
        ProxyOperation::ApproveAddOperator { .. } => "approve_add_operator",
        ProxyOperation::ProposeBanOperator { .. } => "propose_ban_operator",
        ProxyOperation::ApproveBanOperator { .. } => "approve_ban_operator",
    };
    Ok(json!({
        "payload_type": payload_type,
        "decoder_version": "proxy-operation-rust-v1",
        "decoded_payload_json": {
            "operation_type": payload_type,
            "application_id": application_id,
        },
    }))
}

fn decode_proxy_message(application_id: &str, raw_bytes: &[u8]) -> anyhow::Result<Value> {
    let message = bcs::from_bytes::<ProxyMessage>(raw_bytes)?;
    let output = match message {
        ProxyMessage::ProposeAddGenesisMiner { operator, owner } => json!({
            "payload_type": "propose_add_genesis_miner",
            "decoder_version": "proxy-message-rust-v1",
            "decoded_payload_json": {
                "message_type": "propose_add_genesis_miner",
                "application_id": application_id,
                "operator": encode_account(operator),
                "owner": encode_account(owner),
            },
        }),
        ProxyMessage::ApproveAddGenesisMiner { operator, owner } => json!({
            "payload_type": "approve_add_genesis_miner",
            "decoder_version": "proxy-message-rust-v1",
            "decoded_payload_json": {
                "message_type": "approve_add_genesis_miner",
                "application_id": application_id,
                "operator": encode_account(operator),
                "owner": encode_account(owner),
            },
        }),
        ProxyMessage::ProposeRemoveGenesisMiner { operator, owner } => json!({
            "payload_type": "propose_remove_genesis_miner",
            "decoder_version": "proxy-message-rust-v1",
            "decoded_payload_json": {
                "message_type": "propose_remove_genesis_miner",
                "application_id": application_id,
                "operator": encode_account(operator),
                "owner": encode_account(owner),
            },
        }),
        ProxyMessage::ApproveRemoveGenesisMiner { operator, owner } => json!({
            "payload_type": "approve_remove_genesis_miner",
            "decoder_version": "proxy-message-rust-v1",
            "decoded_payload_json": {
                "message_type": "approve_remove_genesis_miner",
                "application_id": application_id,
                "operator": encode_account(operator),
                "owner": encode_account(owner),
            },
        }),
        ProxyMessage::RegisterMiner { owner } => json!({
            "payload_type": "register_miner",
            "decoder_version": "proxy-message-rust-v1",
            "decoded_payload_json": {
                "message_type": "register_miner",
                "application_id": application_id,
                "owner": encode_account(owner),
            },
        }),
        ProxyMessage::DeregisterMiner { owner } => json!({
            "payload_type": "deregister_miner",
            "decoder_version": "proxy-message-rust-v1",
            "decoded_payload_json": {
                "message_type": "deregister_miner",
                "application_id": application_id,
                "owner": encode_account(owner),
            },
        }),
        ProxyMessage::CreateMeme { .. } => json!({
            "payload_type": "create_meme",
            "decoder_version": "proxy-message-rust-v1",
            "decoded_payload_json": {
                "message_type": "create_meme",
                "application_id": application_id,
            },
        }),
        ProxyMessage::CreateMemeExt { bytecode_id, .. } => json!({
            "payload_type": "create_meme_ext",
            "decoder_version": "proxy-message-rust-v1",
            "decoded_payload_json": {
                "message_type": "create_meme_ext",
                "application_id": application_id,
                "bytecode_id": bytecode_id.to_string(),
            },
        }),
        ProxyMessage::MemeCreated { chain_id, token } => json!({
            "payload_type": "meme_created",
            "decoder_version": "proxy-message-rust-v1",
            "decoded_payload_json": {
                "message_type": "meme_created",
                "application_id": application_id,
                "chain_id": chain_id.to_string(),
                "token": token.to_string(),
            },
        }),
        ProxyMessage::ProposeAddOperator { operator, owner } => json!({
            "payload_type": "propose_add_operator",
            "decoder_version": "proxy-message-rust-v1",
            "decoded_payload_json": {
                "message_type": "propose_add_operator",
                "application_id": application_id,
                "operator": encode_account(operator),
                "owner": encode_account(owner),
            },
        }),
        ProxyMessage::ApproveAddOperator { operator, owner } => json!({
            "payload_type": "approve_add_operator",
            "decoder_version": "proxy-message-rust-v1",
            "decoded_payload_json": {
                "message_type": "approve_add_operator",
                "application_id": application_id,
                "operator": encode_account(operator),
                "owner": encode_account(owner),
            },
        }),
        ProxyMessage::ProposeBanOperator { operator, owner } => json!({
            "payload_type": "propose_ban_operator",
            "decoder_version": "proxy-message-rust-v1",
            "decoded_payload_json": {
                "message_type": "propose_ban_operator",
                "application_id": application_id,
                "operator": encode_account(operator),
                "owner": encode_account(owner),
            },
        }),
        ProxyMessage::ApproveBanOperator { operator, owner } => json!({
            "payload_type": "approve_ban_operator",
            "decoder_version": "proxy-message-rust-v1",
            "decoded_payload_json": {
                "message_type": "approve_ban_operator",
                "application_id": application_id,
                "operator": encode_account(operator),
                "owner": encode_account(owner),
            },
        }),
    };
    Ok(output)
}

fn decode_swap_operation(application_id: &str, raw_bytes: &[u8]) -> anyhow::Result<Value> {
    let operation = bcs::from_bytes::<SwapOperation>(raw_bytes)?;
    let (payload_type, decoded_payload_json) = match operation {
        SwapOperation::InitializeLiquidity {
            creator,
            token_0_creator_chain_id,
            token_0,
            amount_0,
            amount_1,
            virtual_liquidity,
            to,
        } => (
            "initialize_liquidity",
            json!({
                "operation_type": "initialize_liquidity",
                "application_id": application_id,
                "creator": encode_account(creator),
                "token_0_creator_chain_id": token_0_creator_chain_id.to_string(),
                "token_0": token_0.to_string(),
                "amount_0": encode_amount(amount_0),
                "amount_1": encode_amount(amount_1),
                "virtual_liquidity": virtual_liquidity,
                "to": encode_option_account(to),
            }),
        ),
        SwapOperation::CreatePool {
            token_0,
            token_1,
            amount_0,
            amount_1,
            to,
        } => (
            "create_pool",
            json!({
                "operation_type": "create_pool",
                "application_id": application_id,
                "token_0": token_0.to_string(),
                "token_1": token_1.map(|value| value.to_string()),
                "amount_0": encode_amount(amount_0),
                "amount_1": encode_amount(amount_1),
                "to": encode_option_account(to),
            }),
        ),
        SwapOperation::UpdatePool {
            token_0,
            token_1,
            transaction,
            token_0_price,
            token_1_price,
            reserve_0,
            reserve_1,
        } => (
            "update_pool",
            json!({
                "operation_type": "update_pool",
                "application_id": application_id,
                "token_0": token_0.to_string(),
                "token_1": token_1.map(|value| value.to_string()),
                "transaction": encode_transaction(transaction),
                "token_0_price": encode_amount(token_0_price),
                "token_1_price": encode_amount(token_1_price),
                "reserve_0": encode_amount(reserve_0),
                "reserve_1": encode_amount(reserve_1),
            }),
        ),
    };
    Ok(json!({
        "payload_type": payload_type,
        "decoder_version": "swap-operation-rust-v1",
        "decoded_payload_json": decoded_payload_json,
    }))
}

fn decode_swap_message(application_id: &str, raw_bytes: &[u8]) -> anyhow::Result<Value> {
    let message = bcs::from_bytes::<SwapMessage>(raw_bytes)?;
    let (payload_type, decoded_payload_json) = match message {
        SwapMessage::InitializeLiquidity {
            creator,
            token_0,
            amount_0,
            amount_1,
            virtual_liquidity,
            to,
        } => (
            "initialize_liquidity",
            json!({
                "message_type": "initialize_liquidity",
                "application_id": application_id,
                "creator": encode_account(creator),
                "token_0": token_0.to_string(),
                "amount_0": encode_amount(amount_0),
                "amount_1": encode_amount(amount_1),
                "virtual_liquidity": virtual_liquidity,
                "to": encode_option_account(to),
            }),
        ),
        SwapMessage::CreatePool {
            creator,
            pool_bytecode_id,
            token_0,
            token_1,
            amount_0,
            amount_1,
            bootstrap_policy,
            to,
        } => (
            "create_pool",
            json!({
                "message_type": "create_pool",
                "application_id": application_id,
                "creator": encode_account(creator),
                "pool_bytecode_id": pool_bytecode_id.to_string(),
                "token_0": token_0.to_string(),
                "token_1": token_1.map(|value| value.to_string()),
                "amount_0": encode_amount(amount_0),
                "amount_1": encode_amount(amount_1),
                "bootstrap_policy": encode_bootstrap_policy(&bootstrap_policy),
                "to": encode_option_account(to),
            }),
        ),
        SwapMessage::PoolCreated {
            creator,
            pool_application,
            token_0,
            token_1,
            amount_0,
            amount_1,
            bootstrap_policy,
            to,
        } => (
            "pool_created",
            json!({
                "message_type": "pool_created",
                "application_id": application_id,
                "creator": encode_account(creator),
                "pool_application": encode_account(pool_application),
                "token_0": token_0.to_string(),
                "token_1": token_1.map(|value| value.to_string()),
                "amount_0": encode_amount(amount_0),
                "amount_1": encode_amount(amount_1),
                "bootstrap_policy": encode_bootstrap_policy(&bootstrap_policy),
                "to": encode_option_account(to),
            }),
        ),
        SwapMessage::CreateUserPool {
            token_0,
            token_1,
            amount_0,
            amount_1,
            to,
        } => (
            "create_user_pool",
            json!({
                "message_type": "create_user_pool",
                "application_id": application_id,
                "token_0": token_0.to_string(),
                "token_1": token_1.map(|value| value.to_string()),
                "amount_0": encode_amount(amount_0),
                "amount_1": encode_amount(amount_1),
                "to": encode_option_account(to),
            }),
        ),
        SwapMessage::UserPoolCreated {
            pool_application,
            token_0,
            token_1,
            amount_0,
            amount_1,
            to,
        } => (
            "user_pool_created",
            json!({
                "message_type": "user_pool_created",
                "application_id": application_id,
                "pool_application": encode_account(pool_application),
                "token_0": token_0.to_string(),
                "token_1": token_1.map(|value| value.to_string()),
                "amount_0": encode_amount(amount_0),
                "amount_1": encode_amount(amount_1),
                "to": encode_option_account(to),
            }),
        ),
        SwapMessage::UpdatePool {
            token_0,
            token_1,
            transaction,
            token_0_price,
            token_1_price,
            reserve_0,
            reserve_1,
        } => (
            "update_pool",
            json!({
                "message_type": "update_pool",
                "application_id": application_id,
                "token_0": token_0.to_string(),
                "token_1": token_1.map(|value| value.to_string()),
                "transaction": encode_transaction(transaction),
                "token_0_price": encode_amount(token_0_price),
                "token_1_price": encode_amount(token_1_price),
                "reserve_0": encode_amount(reserve_0),
                "reserve_1": encode_amount(reserve_1),
            }),
        ),
    };
    Ok(json!({
        "payload_type": payload_type,
        "decoder_version": "swap-message-rust-v1",
        "decoded_payload_json": decoded_payload_json,
    }))
}

fn decode_meme_operation(application_id: &str, raw_bytes: &[u8]) -> anyhow::Result<Value> {
    let operation = bcs::from_bytes::<MemeOperation>(raw_bytes)?;
    let (payload_type, decoded_payload_json) = match operation {
        MemeOperation::CreatorChainId => (
            "creator_chain_id",
            json!({
                "operation_type": "creator_chain_id",
                "application_id": application_id,
            }),
        ),
        MemeOperation::Transfer { to, amount } => (
            "transfer",
            json!({
                "operation_type": "transfer",
                "application_id": application_id,
                "to": encode_account(to),
                "amount": encode_amount(amount),
            }),
        ),
        MemeOperation::TransferFrom { from, to, amount } => (
            "transfer_from",
            json!({
                "operation_type": "transfer_from",
                "application_id": application_id,
                "from": encode_account(from),
                "to": encode_account(to),
                "amount": encode_amount(amount),
            }),
        ),
        MemeOperation::TransferFromApplication { to, amount } => (
            "transfer_from_application",
            json!({
                "operation_type": "transfer_from_application",
                "application_id": application_id,
                "to": encode_account(to),
                "amount": encode_amount(amount),
            }),
        ),
        MemeOperation::InitializeLiquidity {
            pool_application,
            amount_0,
            pool_initialize,
        } => (
            "initialize_liquidity",
            json!({
                "operation_type": "initialize_liquidity",
                "application_id": application_id,
                "pool_application": encode_account(pool_application),
                "amount_0": encode_amount(amount_0),
                "pool_initialize": {
                    "amount_1_in": encode_amount(pool_initialize.amount_1_in),
                    "to": encode_option_account(pool_initialize.to),
                },
            }),
        ),
        MemeOperation::Approve { spender, amount } => (
            "approve",
            json!({
                "operation_type": "approve",
                "application_id": application_id,
                "spender": encode_account(spender),
                "amount": encode_amount(amount),
            }),
        ),
        MemeOperation::TransferOwnership { new_owner } => (
            "transfer_ownership",
            json!({
                "operation_type": "transfer_ownership",
                "application_id": application_id,
                "new_owner": encode_account(new_owner),
            }),
        ),
        MemeOperation::Mine { nonce } => (
            "mine",
            json!({
                "operation_type": "mine",
                "application_id": application_id,
                "nonce_hex": encode_bytes(nonce.as_bytes().as_ref()),
            }),
        ),
        MemeOperation::TransferToCaller { amount } => (
            "transfer_to_caller",
            json!({
                "operation_type": "transfer_to_caller",
                "application_id": application_id,
                "amount": encode_amount(amount),
            }),
        ),
        MemeOperation::Mint { to, amount } => (
            "mint",
            json!({
                "operation_type": "mint",
                "application_id": application_id,
                "to": encode_account(to),
                "amount": encode_amount(amount),
            }),
        ),
        MemeOperation::Redeem { amount } => (
            "redeem",
            json!({
                "operation_type": "redeem",
                "application_id": application_id,
                "amount": encode_option_amount(amount),
            }),
        ),
    };
    Ok(json!({
        "payload_type": payload_type,
        "decoder_version": "meme-operation-rust-v1",
        "decoded_payload_json": decoded_payload_json,
    }))
}

fn decode_meme_message(application_id: &str, raw_bytes: &[u8]) -> anyhow::Result<Value> {
    let message = bcs::from_bytes::<MemeMessage>(raw_bytes)?;
    let (payload_type, decoded_payload_json) = match message {
        MemeMessage::LiquidityFunded => (
            "liquidity_funded",
            json!({
                "message_type": "liquidity_funded",
                "application_id": application_id,
            }),
        ),
        MemeMessage::Transfer { from, to, amount } => (
            "transfer",
            json!({
                "message_type": "transfer",
                "application_id": application_id,
                "from": encode_account(from),
                "to": encode_account(to),
                "amount": encode_amount(amount),
            }),
        ),
        MemeMessage::TransferFrom {
            owner,
            from,
            to,
            amount,
        } => (
            "transfer_from",
            json!({
                "message_type": "transfer_from",
                "application_id": application_id,
                "owner": encode_account(owner),
                "from": encode_account(from),
                "to": encode_account(to),
                "amount": encode_amount(amount),
            }),
        ),
        MemeMessage::TransferFromApplication { caller, to, amount } => (
            "transfer_from_application",
            json!({
                "message_type": "transfer_from_application",
                "application_id": application_id,
                "caller": encode_account(caller),
                "to": encode_account(to),
                "amount": encode_amount(amount),
            }),
        ),
        MemeMessage::InitializeLiquidity {
            caller,
            pool_application,
            amount_0,
            pool_initialize,
        } => (
            "initialize_liquidity",
            json!({
                "message_type": "initialize_liquidity",
                "application_id": application_id,
                "caller": encode_account(caller),
                "pool_application": encode_account(pool_application),
                "amount_0": encode_amount(amount_0),
                "pool_initialize": {
                    "amount_1_in": encode_amount(pool_initialize.amount_1_in),
                    "to": encode_option_account(pool_initialize.to),
                },
            }),
        ),
        MemeMessage::Approve {
            owner,
            spender,
            amount,
        } => (
            "approve",
            json!({
                "message_type": "approve",
                "application_id": application_id,
                "owner": encode_account(owner),
                "spender": encode_account(spender),
                "amount": encode_amount(amount),
            }),
        ),
        MemeMessage::TransferOwnership { owner, new_owner } => (
            "transfer_ownership",
            json!({
                "message_type": "transfer_ownership",
                "application_id": application_id,
                "owner": encode_account(owner),
                "new_owner": encode_account(new_owner),
            }),
        ),
        MemeMessage::Mint { to, amount } => (
            "mint",
            json!({
                "message_type": "mint",
                "application_id": application_id,
                "to": encode_account(to),
                "amount": encode_amount(amount),
            }),
        ),
        MemeMessage::Redeem { owner, amount } => (
            "redeem",
            json!({
                "message_type": "redeem",
                "application_id": application_id,
                "owner": encode_account(owner),
                "amount": encode_option_amount(amount),
            }),
        ),
    };
    Ok(json!({
        "payload_type": payload_type,
        "decoder_version": "meme-message-rust-v1",
        "decoded_payload_json": decoded_payload_json,
    }))
}

fn decode_ams_operation(application_id: &str, raw_bytes: &[u8]) -> anyhow::Result<Value> {
    let operation = bcs::from_bytes::<AmsOperation>(raw_bytes)?;
    let output = match operation {
        AmsOperation::AddApplicationType { application_type } => json!({
            "payload_type": "add_application_type",
            "decoder_version": "ams-operation-rust-v1",
            "decoded_payload_json": {
                "operation_type": "add_application_type",
                "application_id": application_id,
                "application_type": application_type,
            },
        }),
        AmsOperation::Register { .. } => json!({
            "payload_type": "register",
            "decoder_version": "ams-operation-rust-v1",
            "decoded_payload_json": {
                "operation_type": "register",
                "application_id": application_id,
            },
        }),
        AmsOperation::Claim { .. } => json!({
            "payload_type": "claim",
            "decoder_version": "ams-operation-rust-v1",
            "decoded_payload_json": {
                "operation_type": "claim",
                "application_id": application_id,
            },
        }),
        AmsOperation::Update { .. } => json!({
            "payload_type": "update",
            "decoder_version": "ams-operation-rust-v1",
            "decoded_payload_json": {
                "operation_type": "update",
                "application_id": application_id,
            },
        }),
    };
    Ok(output)
}

fn decode_ams_message(application_id: &str, raw_bytes: &[u8]) -> anyhow::Result<Value> {
    let message = bcs::from_bytes::<AmsMessage>(raw_bytes)?;
    let output = match message {
        AmsMessage::Register { metadata } => json!({
            "payload_type": "register",
            "decoder_version": "ams-message-rust-v1",
            "decoded_payload_json": {
                "message_type": "register",
                "application_id": application_id,
                "registered_application_id": metadata.application_id.to_string(),
                "application_type": metadata.application_type,
                "application_name": metadata.application_name,
            },
        }),
        AmsMessage::Claim {
            application_id: claimed_application_id,
        } => json!({
            "payload_type": "claim",
            "decoder_version": "ams-message-rust-v1",
            "decoded_payload_json": {
                "message_type": "claim",
                "application_id": application_id,
                "claimed_application_id": claimed_application_id.to_string(),
            },
        }),
        AmsMessage::AddApplicationType {
            owner,
            application_type,
        } => json!({
            "payload_type": "add_application_type",
            "decoder_version": "ams-message-rust-v1",
            "decoded_payload_json": {
                "message_type": "add_application_type",
                "application_id": application_id,
                "owner": encode_account(owner),
                "application_type": application_type,
            },
        }),
        AmsMessage::Update {
            owner,
            application_id: updated_application_id,
            metadata,
        } => json!({
            "payload_type": "update",
            "decoder_version": "ams-message-rust-v1",
            "decoded_payload_json": {
                "message_type": "update",
                "application_id": application_id,
                "owner": encode_account(owner),
                "updated_application_id": updated_application_id.to_string(),
                "application_type": metadata.application_type,
                "application_name": metadata.application_name,
            },
        }),
    };
    Ok(output)
}

fn decode_blob_gateway_operation(application_id: &str, raw_bytes: &[u8]) -> anyhow::Result<Value> {
    let operation = bcs::from_bytes::<BlobGatewayOperation>(raw_bytes)?;
    let output = match operation {
        BlobGatewayOperation::Register {
            store_type,
            data_type,
            blob_hash,
        } => json!({
            "payload_type": "blob_gateway_register",
            "decoder_version": "blob-gateway-operation-rust-v1",
            "decoded_payload_json": {
                "operation_type": "register",
                "application_id": application_id,
                "store_type": format!("{store_type:?}").to_lowercase(),
                "data_type": format!("{data_type:?}").to_lowercase(),
                "blob_hash_hex": encode_bytes(blob_hash.as_bytes().as_ref()),
            },
        }),
    };
    Ok(output)
}

fn decode_blob_gateway_message(application_id: &str, raw_bytes: &[u8]) -> anyhow::Result<Value> {
    let message = bcs::from_bytes::<BlobGatewayMessage>(raw_bytes)?;
    let output = match message {
        BlobGatewayMessage::Register { blob_data } => json!({
            "payload_type": "blob_gateway_register",
            "decoder_version": "blob-gateway-message-rust-v1",
            "decoded_payload_json": {
                "message_type": "register",
                "application_id": application_id,
                "store_type": format!("{:?}", blob_data.store_type).to_lowercase(),
                "data_type": format!("{:?}", blob_data.data_type).to_lowercase(),
                "blob_hash_hex": encode_bytes(blob_data.blob_hash.as_bytes().as_ref()),
                "creator": encode_account(blob_data.creator),
                "created_at_micros": blob_data.created_at.micros(),
            },
        }),
    };
    Ok(output)
}

fn encode_transaction(transaction: Transaction) -> Value {
    json!({
        "transaction_id": transaction.transaction_id,
        "transaction_type": encode_transaction_type(transaction.transaction_type),
        "from": encode_account(transaction.from),
        "amount_0_in": encode_option_amount(transaction.amount_0_in),
        "amount_0_out": encode_option_amount(transaction.amount_0_out),
        "amount_1_in": encode_option_amount(transaction.amount_1_in),
        "amount_1_out": encode_option_amount(transaction.amount_1_out),
        "liquidity": encode_option_amount(transaction.liquidity),
        "created_at_micros": transaction.created_at.micros(),
    })
}

fn encode_transaction_type(transaction_type: TransactionType) -> &'static str {
    match transaction_type {
        TransactionType::BuyToken0 => "buy_token_0",
        TransactionType::SellToken0 => "sell_token_0",
        TransactionType::AddLiquidity => "add_liquidity",
        TransactionType::RemoveLiquidity => "remove_liquidity",
    }
}

fn encode_option_timestamp(value: Option<Timestamp>) -> Option<u64> {
    value.map(|timestamp| timestamp.micros())
}

fn encode_bootstrap_policy(policy: &BootstrapPolicy) -> Value {
    match policy {
        BootstrapPolicy::UserCreatePool => json!({
            "kind": "user_create_pool"
        }),
        BootstrapPolicy::MemeInitializeLiquidity {
            virtual_initial_liquidity,
        } => json!({
            "kind": "meme_initialize_liquidity",
            "virtual_initial_liquidity": virtual_initial_liquidity,
        }),
    }
}

fn encode_option_amount(value: Option<Amount>) -> Option<String> {
    value.map(encode_amount)
}

fn encode_amount(value: Amount) -> String {
    u128::from(value).to_string()
}

fn encode_option_account(value: Option<Account>) -> Option<Value> {
    value.map(encode_account)
}

fn encode_account(value: Account) -> Value {
    json!({
        "chain_id": encode_bytes(value.chain_id.0.as_bytes().as_ref()),
        "owner": encode_account_owner(value.owner),
    })
}

fn encode_account_owner(value: AccountOwner) -> Option<String> {
    match value {
        AccountOwner::Reserved(_) => None,
        AccountOwner::Address32(hash) => {
            Some(format!("0x{}", encode_bytes(hash.as_bytes().as_ref())))
        }
        AccountOwner::Address20(bytes) => Some(format!("0x{}", encode_bytes(bytes.as_ref()))),
    }
}

fn encode_bytes(bytes: &[u8]) -> String {
    let mut output = String::with_capacity(bytes.len() * 2);
    for byte in bytes {
        output.push_str(&format!("{byte:02x}"));
    }
    output
}

fn decode_hex(input: &str) -> anyhow::Result<Vec<u8>> {
    if input.len() % 2 != 0 {
        anyhow::bail!("invalid hex length");
    }
    let mut bytes = Vec::with_capacity(input.len() / 2);
    let chars: Vec<char> = input.chars().collect();
    let mut index = 0;
    while index < chars.len() {
        let high = chars[index]
            .to_digit(16)
            .ok_or_else(|| anyhow::anyhow!("invalid hex digit"))?;
        let low = chars[index + 1]
            .to_digit(16)
            .ok_or_else(|| anyhow::anyhow!("invalid hex digit"))?;
        bytes.push(((high << 4) | low) as u8);
        index += 2;
    }
    Ok(bytes)
}
