use super::meme::*;

use linera_sdk::linera_base_types::{
    Amount, BcsSignable, BlockHeight, CryptoHash, TimeDelta, Timestamp,
};
use serde::{Deserialize, Serialize};

use std::str::FromStr;

#[test]
fn test_mining_info_new_with_supply() {
    let mining_supply = Amount::from_str("10000000").unwrap(); // 1000 万个代币
    let now = Timestamp::now();

    let mining_info = MiningInfo::new(mining_supply, now);

    let expected_initial_target =
        CryptoHash::from_str("00000000FFFF0000000000000000000000000000000000000000000000000000")
            .unwrap();
    assert_eq!(mining_info.initial_target, expected_initial_target);

    assert_eq!(mining_info.target, expected_initial_target);
    assert_eq!(mining_info.new_target, expected_initial_target);

    assert_eq!(mining_info.empty_block_reward_percent, 100);

    let expected_halving_cycle = TimeDelta::from_secs(3600 * 24 * 365);
    assert_eq!(mining_info.halving_cycle, expected_halving_cycle);
    assert_eq!(
        mining_info.next_halving_at,
        now.saturating_add(expected_halving_cycle)
    );

    let expected_initial_reward = Amount::from_str("1.7").unwrap().saturating_mul(
        mining_supply
            .saturating_div(Amount::from_tokens(21000000).into())
            .into(),
    );
    assert_eq!(mining_info.initial_reward_amount, expected_initial_reward);
    assert_eq!(mining_info.reward_amount, expected_initial_reward);

    assert_eq!(mining_info.target_adjustment_blocks, 2160);

    let block_interval_seconds = 5;
    let expected_block_duration = TimeDelta::from_secs((2160 * block_interval_seconds) as u64);
    assert_eq!(mining_info.block_duration, expected_block_duration);
    assert_eq!(mining_info.target_block_duration, expected_block_duration);

    assert_eq!(mining_info.mining_height, BlockHeight(0));
    assert_eq!(mining_info.mining_executions, 0);

    #[derive(Debug, Serialize, Deserialize)]
    struct Nonce(String);
    impl BcsSignable<'_> for Nonce {}

    let initial_nonce = CryptoHash::new(&Nonce("Initial mining nonce".to_string()));
    assert_eq!(mining_info.previous_nonce, initial_nonce);
}

#[test]
fn test_mining_info_new_with_zero_supply() {
    let mining_supply = Amount::from_str("0").unwrap();
    let now = Timestamp::now();

    let mining_info = MiningInfo::new(mining_supply, now);

    let expected_initial_target =
        CryptoHash::from_str("00000000FFFF0000000000000000000000000000000000000000000000000000")
            .unwrap();
    assert_eq!(mining_info.initial_target, expected_initial_target);

    assert_eq!(mining_info.empty_block_reward_percent, 100);

    let expected_initial_reward = Amount::from_str("1.7")
        .unwrap()
        .saturating_mul((0 as u128).into());
    assert_eq!(mining_info.initial_reward_amount, expected_initial_reward);
}
