use linera_sdk::linera_base_types::Amount;

pub fn open_chain_fee_budget() -> Amount {
    Amount::from_attos(Amount::ONE.saturating_div(Amount::from_attos(10)))
}
