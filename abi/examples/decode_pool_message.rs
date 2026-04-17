use std::{env, process};

use abi::swap::pool::PoolMessage;

fn hex_value(byte: u8) -> Result<u8, String> {
    match byte {
        b'0'..=b'9' => Ok(byte - b'0'),
        b'a'..=b'f' => Ok(byte - b'a' + 10),
        b'A'..=b'F' => Ok(byte - b'A' + 10),
        _ => Err(format!("invalid hex character: {}", byte as char)),
    }
}

fn decode_hex(input: &str) -> Result<Vec<u8>, String> {
    let trimmed = input.trim().strip_prefix("0x").unwrap_or(input.trim());
    if trimmed.len() % 2 != 0 {
        return Err("hex input must have even length".to_string());
    }

    let mut bytes = Vec::with_capacity(trimmed.len() / 2);
    for pair in trimmed.as_bytes().chunks_exact(2) {
        let high = hex_value(pair[0])?;
        let low = hex_value(pair[1])?;
        bytes.push((high << 4) | low);
    }
    Ok(bytes)
}

fn main() {
    let mut args = env::args().skip(1).collect::<Vec<_>>();
    if args.is_empty() {
        eprintln!("usage: cargo run -p abi --example decode_pool_message -- <userBytesHex|[1,2,3,...]> [...]");
        process::exit(2);
    }

    for raw in args.drain(..) {
        let bytes = if raw.trim_start().starts_with('[') {
            match serde_json::from_str::<Vec<u8>>(&raw) {
                Ok(bytes) => bytes,
                Err(error) => {
                    eprintln!("{raw}\njson array decode failed: {error}");
                    process::exit(1);
                }
            }
        } else {
            match decode_hex(&raw) {
                Ok(bytes) => bytes,
                Err(error) => {
                    eprintln!("{raw}\nhex decode failed: {error}");
                    process::exit(1);
                }
            }
        };

        let message = match bcs::from_bytes::<PoolMessage>(&bytes) {
            Ok(message) => message,
            Err(error) => {
                eprintln!("{raw}\nbcs decode failed: {error}");
                process::exit(1);
            }
        };

        println!("{}", serde_json::to_string_pretty(&message).unwrap());
    }
}
