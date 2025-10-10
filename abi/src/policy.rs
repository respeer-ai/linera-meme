use linera_sdk::linera_base_types::Amount;

pub fn open_chain_fee_budget() -> Amount {
    Amount::ONE.saturating_mul(1)
}
