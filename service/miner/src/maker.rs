use linera_base::{data_types::Amount, identifiers::ApplicationId};

pub struct Swap {
    amount_0_in: Option<Amount>,
    amount_1_in: Option<Amount>,
}

impl Swap {
    pub fn is_valid(&self) -> bool {
        (self.amount_0_in.is_some() && self.amount_0_in.unwrap() > Amount::ZERO)
            || (self.amount_1_in.is_some() && self.amount_1_in.unwrap() > Amount::ZERO)
    }

    pub fn amount_0_in(&self) -> Option<Amount> {
        self.amount_0_in
    }

    pub fn amount_1_in(&self) -> Option<Amount> {
        self.amount_1_in
    }
}

pub struct Maker {
    swap_application_id: ApplicationId,
}

impl Maker {
    pub fn new(swap_application_id: ApplicationId) -> Self {
        Self {
            swap_application_id,
        }
    }

    fn construct_swap(&self) -> Swap {
        Swap {
            amount_0_in: Some(Amount::from_tokens(10)),
            amount_1_in: None,
        }
    }

    pub fn create_deal(&self) {}
}
