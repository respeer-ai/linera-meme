// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

use crate::{
    interfaces::state::StateInterface,
    state::{errors::StateError, MemeState},
};
use abi::{
    meme::{InstantiationArgument, Liquidity, Meme, MiningInfo},
    store_type::StoreType,
};
use async_trait::async_trait;
use linera_sdk::linera_base_types::{
    Account, AccountOwner, Amount, ApplicationId, BlockHeight, ChainId, CryptoHash,
};
use std::{cell::RefCell, rc::Rc};

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

    async fn initialize_liquidity(
        &mut self,
        liquidity: Liquidity,
        swap_creator_chain_id: ChainId,
    ) -> Result<(), StateError> {
        self.state
            .borrow_mut()
            .initialize_liquidity(liquidity, swap_creator_chain_id)
            .await
    }

    fn instantiate(
        &mut self,
        owner: Account,
        application: Account,
        argument: InstantiationArgument,
        enable_mining: bool,
        mining_supply: Option<Amount>,
    ) -> Result<(), StateError> {
        self.state.borrow_mut().instantiate(
            owner,
            application,
            argument,
            enable_mining,
            mining_supply,
        )
    }

    async fn mint(&mut self, to: Account, amount: Amount) -> Result<(), StateError> {
        self.state.borrow_mut().mint(to, amount).await
    }

    fn proxy_application_id(&self) -> Option<ApplicationId> {
        self.state.borrow().proxy_application_id()
    }

    fn blob_gateway_application_id(&self) -> Option<ApplicationId> {
        self.state.borrow().blob_gateway_application_id()
    }

    fn ams_application_id(&self) -> Option<ApplicationId> {
        self.state.borrow().ams_application_id()
    }

    fn swap_application_id(&self) -> Option<ApplicationId> {
        self.state.borrow().swap_application_id()
    }

    async fn transfer_(
        &mut self,
        from: Account,
        to: Account,
        amount: Amount,
    ) -> Result<(), StateError> {
        self.state.borrow_mut().transfer_(from, to, amount).await
    }

    async fn transfer(
        &mut self,
        from: Account,
        to: Account,
        amount: Amount,
    ) -> Result<(), StateError> {
        self.state.borrow_mut().transfer(from, to, amount).await
    }

    async fn transfer_ensure(
        &mut self,
        from: Account,
        to: Account,
        amount: Amount,
    ) -> Result<(), StateError> {
        self.state
            .borrow_mut()
            .transfer_ensure(from, to, amount)
            .await
    }

    async fn approve(
        &mut self,
        owner: Account,
        spender: Account,
        amount: Amount,
    ) -> Result<(), StateError> {
        self.state
            .borrow_mut()
            .approve(owner, spender, amount)
            .await
    }

    async fn transfer_from(
        &mut self,
        owner: Account,
        from: Account,
        to: Account,
        amount: Amount,
    ) -> Result<(), StateError> {
        self.state
            .borrow_mut()
            .transfer_from(owner, from, to, amount)
            .await
    }

    fn owner(&self) -> Account {
        self.state.borrow().owner()
    }

    fn owner_signer(&self) -> AccountOwner {
        self.state.borrow().owner_signer()
    }

    async fn balance_of(&self, owner: Account) -> Amount {
        self.state.borrow().balance_of(owner).await
    }

    async fn allowance_of(&self, owner: Account, spender: Account) -> Amount {
        self.state.borrow().allowance_of(owner, spender).await
    }

    fn initial_owner_balance(&self) -> Amount {
        self.state.borrow().initial_owner_balance()
    }

    fn transfer_ownership(&mut self, owner: Account, new_owner: Account) -> Result<(), StateError> {
        self.state.borrow_mut().transfer_ownership(owner, new_owner)
    }

    fn name(&self) -> String {
        self.state.borrow().name()
    }

    fn logo_store_type(&self) -> StoreType {
        self.state.borrow().logo_store_type()
    }

    fn logo(&self) -> CryptoHash {
        self.state.borrow().logo()
    }

    fn description(&self) -> String {
        self.state.borrow().description()
    }

    fn twitter(&self) -> Option<String> {
        self.state.borrow().twitter()
    }

    fn telegram(&self) -> Option<String> {
        self.state.borrow().telegram()
    }

    fn discord(&self) -> Option<String> {
        self.state.borrow().discord()
    }

    fn website(&self) -> Option<String> {
        self.state.borrow().website()
    }

    fn github(&self) -> Option<String> {
        self.state.borrow().github()
    }

    fn meme(&self) -> Meme {
        self.state.borrow().meme()
    }

    fn mining_target(&self) -> CryptoHash {
        self.state.borrow().mining_target()
    }

    fn previous_nonce(&self) -> CryptoHash {
        self.state.borrow().previous_nonce()
    }

    fn mining_height(&self) -> BlockHeight {
        self.state.borrow().mining_height()
    }

    fn mining_info(&self) -> MiningInfo {
        self.state.borrow().mining_info()
    }

    fn update_mining_info(&mut self, info: MiningInfo) {
        self.state.borrow_mut().update_mining_info(info);
    }
}
