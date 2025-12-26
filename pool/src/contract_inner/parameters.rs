use crate::interfaces::parameters::ParametersInterface;
use abi::swap::pool::PoolParameters;
use linera_sdk::{
    linera_base_types::{Account, ApplicationId},
    Contract,
};
use runtime::{contract::ContractRuntimeAdapter, interfaces::base::BaseRuntimeContext};

impl ParametersInterface for PoolParameters {
    fn creator(&mut self) -> Account {
        self.creator
    }

    fn token_0(&mut self) -> ApplicationId {
        self.token_0
    }

    fn token_1(&mut self) -> Option<ApplicationId> {
        self.token_1
    }
}

impl<T, M> ParametersInterface for ContractRuntimeAdapter<T, M>
where
    T: Contract<Message = M>,
    T::Parameters: ParametersInterface,
{
    fn creator(&mut self) -> Account {
        self.application_parameters().creator()
    }

    fn token_0(&mut self) -> ApplicationId {
        self.application_parameters().token_0()
    }

    fn token_1(&mut self) -> Option<ApplicationId> {
        self.application_parameters().token_1()
    }
}
