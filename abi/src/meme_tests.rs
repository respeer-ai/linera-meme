use super::meme::*;

use linera_sdk::linera_base_types::{
    Amount, BcsSignable, BlockHeight, CryptoHash, TimeDelta, Timestamp,
};
use serde::{Deserialize, Serialize};

use primitive_types::U256;
use std::str::FromStr;

#[test]
fn test_mining_info_new_with_supply() {
    let _ = env_logger::builder().is_test(true).try_init();

    let mining_supply = Amount::from_str("10000000").unwrap(); // 1000 万个代币
    let now = Timestamp::now();

    let mining_info = MiningInfo::new(mining_supply, now);

    let expected_initial_target =
        CryptoHash::from_str("00000fffffffffffffffffffffffffffffffffffffffffffffffffffffffffff")
            .unwrap();
    assert_eq!(mining_info.initial_target, expected_initial_target);

    assert_eq!(mining_info.target, expected_initial_target);

    assert_eq!(mining_info.empty_block_reward_percent, 100);

    let expected_halving_cycle = TimeDelta::from_secs(3600 * 24 * 365);
    assert_eq!(mining_info.halving_cycle, expected_halving_cycle);
    assert_eq!(
        mining_info.next_halving_at,
        now.saturating_add(expected_halving_cycle)
    );

    let expected_initial_reward = Amount::from_attos(
        U256::from(u128::from(Amount::from_str("1.7").unwrap()))
            .checked_mul(U256::from(u128::from(mining_supply)))
            .unwrap()
            .checked_div(U256::from(u128::from(Amount::from_tokens(21000000))))
            .unwrap()
            .as_u128(),
    );

    assert!(
        mining_info.initial_reward_amount > Amount::ZERO,
        "Invalid amount"
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
    let _ = env_logger::builder().is_test(true).try_init();

    let mining_supply = Amount::from_str("0").unwrap();
    let now = Timestamp::now();

    let mining_info = MiningInfo::new(mining_supply, now);

    let expected_initial_target =
        CryptoHash::from_str("00000fffffffffffffffffffffffffffffffffffffffffffffffffffffffffff")
            .unwrap();
    assert_eq!(mining_info.initial_target, expected_initial_target);
    assert_eq!(mining_info.empty_block_reward_percent, 100);
    assert_eq!(mining_info.initial_reward_amount, 0.into());
}

#[test]
fn test_mining_info_halving_cycle() {
    let _ = env_logger::builder().is_test(true).try_init();

    let mining_supply = Amount::from_str("21000000").unwrap();
    let now = Timestamp::now();

    let mut mining_info = MiningInfo::new(mining_supply, now);

    let initial_reward = mining_info.reward_amount;
    assert!(initial_reward > Amount::ZERO);

    let halving_cycle = mining_info.halving_cycle;
    let first_halving_at = mining_info.next_halving_at;

    let after_first_halving = first_halving_at;
    mining_info.try_half(after_first_halving);

    assert_eq!(
        mining_info.reward_amount,
        initial_reward.saturating_div(2),
        "Reward should be halved after first cycle"
    );

    assert_eq!(
        mining_info.next_halving_at,
        first_halving_at.saturating_add(halving_cycle),
        "Next halving timestamp should move forward one cycle"
    );

    let after_second_halving = mining_info.next_halving_at;
    let reward_after_first = mining_info.reward_amount;

    mining_info.try_half(after_second_halving);

    assert_eq!(
        mining_info.reward_amount,
        reward_after_first.saturating_div(2),
        "Reward should be halved again after second cycle"
    );
}

#[test]
fn test_adjust_target_exact_duration_no_change() {
    let _ = env_logger::builder().is_test(true).try_init();

    let mining_supply = Amount::from_str("21000000").unwrap();
    let start = Timestamp::now();

    let mut info = MiningInfo::new(mining_supply, start);

    info.cumulative_blocks = info.target_adjustment_blocks;

    let original_target = info.target;
    let target_duration = info.target_block_duration;

    let now = start.saturating_add(target_duration);

    info.try_adjust_target(now);

    assert_eq!(
        info.target, original_target,
        "Target should not change if elapsed == target_block_duration"
    );
    assert_eq!(info.cumulative_blocks, 0);
    assert_eq!(info.block_duration, target_duration);
    assert_eq!(info.last_target_adjusted_at, now);
}

#[test]
fn test_adjust_target_faster_blocks_increase_difficulty() {
    let _ = env_logger::builder().is_test(true).try_init();

    let mining_supply = Amount::from_str("21000000").unwrap();
    let start = Timestamp::now();

    let mut info = MiningInfo::new(mining_supply, start);
    info.cumulative_blocks = info.target_adjustment_blocks;

    let original_target = info.target;

    let fast_duration = TimeDelta::from_secs(2 * 3600);
    let now = start.saturating_add(fast_duration);

    info.try_adjust_target(now);

    assert!(
        info.target < original_target,
        "Target should decrease (difficulty increase) when blocks are mined too fast"
    );
    assert_eq!(info.block_duration, fast_duration);
    assert_eq!(info.cumulative_blocks, 0);
}

#[test]
fn test_adjust_target_slower_blocks_decrease_difficulty() {
    let _ = env_logger::builder().is_test(true).try_init();

    let mining_supply = Amount::from_str("21000000").unwrap();
    let start = Timestamp::now();

    let mut info = MiningInfo::new(mining_supply, start);
    info.cumulative_blocks = info.target_adjustment_blocks;

    let original_target = info.target;

    let slow_duration = TimeDelta::from_secs(6 * 3600);
    let now = start.saturating_add(slow_duration);

    info.try_adjust_target(now);

    assert!(
        info.target > original_target,
        "Target should increase (difficulty decrease) when blocks are mined too slowly"
    );
    assert_eq!(info.block_duration, slow_duration);
    assert_eq!(info.cumulative_blocks, 0);
}

#[test]
fn test_adjust_target_extreme_elapsed_time_safe() {
    let _ = env_logger::builder().is_test(true).try_init();

    let mining_supply = Amount::from_str("21000000").unwrap();
    let start = Timestamp::now();

    let mut info = MiningInfo::new(mining_supply, start);
    info.cumulative_blocks = info.target_adjustment_blocks;

    let original_target = info.target;

    let extreme_duration =
        TimeDelta::from_secs(info.target_block_duration.as_duration().as_secs() * 100);
    let now = start.saturating_add(extreme_duration);

    info.try_adjust_target(now);

    assert!(
        info.target > original_target,
        "Extreme slow mining should increase target"
    );

    let zero = CryptoHash::from([0u8; 32]);
    assert_ne!(info.target, zero, "Target must never be zero");

    assert_eq!(info.cumulative_blocks, 0);
    assert_eq!(info.block_duration, extreme_duration);
    assert_eq!(info.last_target_adjusted_at, now);
}
