use std::{cell::RefCell, rc::Rc};

use abi::meme::{InitializeArgument, Liquidity, MiningInfo, StateInstantiationArgument};
use async_trait::async_trait;
use linera_sdk::linera_base_types::{Account, Amount, ApplicationId, ChainId};

use crate::{
    interfaces::state::StateInterface,
    state::{errors::StateError, MemeState},
};

pub struct StateAdapter {
    state: Rc<RefCell<MemeState>>,
}

impl StateAdapter {
    pub fn new(state: Rc<RefCell<MemeState>>) -> Self {
        Self { state }
    }
}

#[async_trait(?Send)]
impl StateInterface for StateAdapter {
    type Error = StateError;

    fn instantiate(&mut self, argument: StateInstantiationArgument) {
        self.state.borrow_mut().instantiate(argument);
    }

    async fn business_application_id(&mut self) -> Result<ApplicationId, Self::Error> {
        self.state.borrow_mut().business_application_id().await
    }

    async fn handoff(
        &mut self,
        new_business_application_id: ApplicationId,
    ) -> Result<(), Self::Error> {
        self.state
            .borrow_mut()
            .handoff(new_business_application_id)
            .await
    }

    async fn operator(&mut self) -> Result<Account, Self::Error> {
        self.state.borrow_mut().operator().await
    }

    async fn owner(&self) -> Result<Account, Self::Error> {
        self.state.borrow().owner().await
    }

    async fn balance_of(&self, owner: Account) -> Result<Amount, Self::Error> {
        self.state.borrow().balance_of(owner).await
    }

    async fn transfer(
        &mut self,
        from: Account,
        to: Account,
        amount: Amount,
    ) -> Result<(), Self::Error> {
        self.state.borrow_mut().transfer(from, to, amount).await
    }

    async fn allowance_of(&self, owner: Account, spender: Account) -> Result<Amount, Self::Error> {
        self.state.borrow().allowance_of(owner, spender).await
    }

    async fn transfer_from(
        &mut self,
        origin: Account,
        from: Account,
        to: Account,
        amount: Amount,
    ) -> Result<(), Self::Error> {
        self.state
            .borrow_mut()
            .transfer_from(origin, from, to, amount)
            .await
    }

    async fn approve(
        &mut self,
        owner: Account,
        spender: Account,
        amount: Amount,
    ) -> Result<(), Self::Error> {
        self.state.borrow_mut().approve(owner, spender, amount).await
    }

    async fn initialize(&mut self, argument: InitializeArgument) -> Result<(), Self::Error> {
        self.state.borrow_mut().initialize(argument).await
    }

    async fn initialize_liquidity(
        &mut self,
        liquidity: Liquidity,
        swap_creator_chain_id: ChainId,
        enable_mining: bool,
        mining_supply: Option<Amount>,
    ) -> Result<(), Self::Error> {
        self.state
            .borrow_mut()
            .initialize_liquidity(liquidity, swap_creator_chain_id, enable_mining, mining_supply)
            .await
    }

    async fn mint(&mut self, to: Account, amount: Amount) -> Result<(), Self::Error> {
        self.state.borrow_mut().mint(to, amount).await
    }

    async fn transfer_ownership(
        &mut self,
        owner: Account,
        new_owner: Account,
    ) -> Result<(), Self::Error> {
        self.state
            .borrow_mut()
            .transfer_ownership(owner, new_owner)
            .await
    }

    async fn mining_info(&self) -> Result<MiningInfo, Self::Error> {
        self.state.borrow().mining_info().await
    }

    async fn mining_reward(
        &mut self,
        owner: Account,
        reward_amount: Amount,
        mining_info: MiningInfo,
    ) -> Result<(), Self::Error> {
        self.state
            .borrow_mut()
            .mining_reward(owner, reward_amount, mining_info)
            .await
    }

    async fn swap_application_id(&self) -> Result<Option<ApplicationId>, Self::Error> {
        self.state.borrow().swap_application_id().await
    }

    async fn proxy_application_id(&self) -> Result<Option<ApplicationId>, Self::Error> {
        self.state.borrow().proxy_application_id().await
    }

    async fn start_mining(&mut self) -> Result<(), Self::Error> {
        self.state.borrow_mut().start_mining().await
    }
}
