use crate::interfaces::parameters::ParametersInterface;
use abi::meme::{Liquidity, MemeParameters};
use linera_sdk::{
    linera_base_types::{Account, AccountOwner, Amount, ChainId},
    Contract,
};
use runtime::{contract::ContractRuntimeAdapter, interfaces::base::BaseRuntimeContext};

impl ParametersInterface for MemeParameters {
    fn creator(&mut self) -> Account {
        self.creator
    }

    fn creator_signer(&mut self) -> AccountOwner {
        self.creator.owner
    }

    fn virtual_initial_liquidity(&mut self) -> bool {
        self.virtual_initial_liquidity
    }

    fn initial_liquidity(&mut self) -> Option<Liquidity> {
        self.initial_liquidity.clone()
    }

    // TODO: could be in runtime line MemeRuntimeContext ?
    fn swap_creator_chain_id(&mut self) -> ChainId {
        self.swap_creator_chain_id
    }

    fn enable_mining(&mut self) -> bool {
        self.enable_mining
    }

    fn mining_supply(&mut self) -> Option<Amount> {
        self.mining_supply
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

    fn creator_signer(&mut self) -> AccountOwner {
        self.application_parameters().creator_signer()
    }

    fn virtual_initial_liquidity(&mut self) -> bool {
        self.application_parameters().virtual_initial_liquidity()
    }

    fn initial_liquidity(&mut self) -> Option<Liquidity> {
        self.application_parameters().initial_liquidity()
    }

    fn swap_creator_chain_id(&mut self) -> ChainId {
        self.application_parameters().swap_creator_chain_id()
    }

    fn enable_mining(&mut self) -> bool {
        self.application_parameters().enable_mining()
    }

    fn mining_supply(&mut self) -> Option<Amount> {
        self.application_parameters().mining_supply()
    }
}
