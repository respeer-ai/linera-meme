use linera_sdk::linera_base_types::{Account, ApplicationId};

pub trait ParametersInterface {
    fn creator(&mut self) -> Account;
    fn token_0(&mut self) -> ApplicationId;
    fn token_1(&mut self) -> Option<ApplicationId>;
}
