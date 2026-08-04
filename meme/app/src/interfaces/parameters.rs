use abi::meme::Liquidity;
use linera_sdk::linera_base_types::{Account, AccountOwner, Amount, ChainId};

pub trait ParametersInterface {
    fn creator(&mut self) -> Account;
    fn creator_signer(&mut self) -> AccountOwner;
    fn virtual_initial_liquidity(&mut self) -> bool;
    fn initial_liquidity(&mut self) -> Option<Liquidity>;
    fn swap_creator_chain_id(&mut self) -> ChainId;
    fn enable_mining(&mut self) -> bool;
    fn mining_supply(&mut self) -> Option<Amount>;
}
