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
use linera_sdk::{
    ensure,
    linera_base_types::{
        Account, AccountOwner, Amount, ApplicationId, BlockHeight, ChainId, CryptoHash, Timestamp,
    },
};
use std::collections::HashMap;

impl MemeState {
    fn initialize_mining_info(&mut self, mining_supply: Amount, now: Timestamp) {
        self.mining_info
            .set(Some(MiningInfo::new(mining_supply, now)));
    }

    fn mining_reward_amount(&self) -> Amount {
        self.mining_info.get().as_ref().unwrap().reward_amount
    }
}

#[async_trait(?Send)]
impl StateInterface for MemeState {
    type Error = StateError;

    fn _initial_liquidity(&self) -> Option<Liquidity> {
        self.initial_liquidity.get().clone()
    }

    async fn initialize_liquidity(
        &mut self,
        mut liquidity: Liquidity,
        swap_creator_chain_id: ChainId,
        enable_mining: bool,
        mining_supply: Option<Amount>,
    ) -> Result<(), StateError> {
        assert!(
            liquidity.fungible_amount >= Amount::ZERO,
            "Invalid initial liquidity"
        );
        assert!(
            liquidity.native_amount >= Amount::ZERO,
            "Invalid initial liquidity"
        );

        let holder_balance = self
            .balance_of(self.holder.get().as_ref().unwrap().clone())
            .await;

        let mining_supply = if enable_mining {
            mining_supply.unwrap_or(holder_balance)
        } else {
            Amount::ZERO
        };

        assert!(
            holder_balance >= liquidity.fungible_amount,
            "Invalid initial supply"
        );
        assert!(holder_balance >= mining_supply, "Invalid mining supply");

        // TODO: liquidity should <= total_supply - mining_supply, if not, adjust it
        let max_liquidity_amount = holder_balance.saturating_sub(mining_supply);

        if enable_mining {
            if liquidity.fungible_amount > max_liquidity_amount {
                liquidity.fungible_amount = holder_balance.saturating_sub(mining_supply)
            }
        }

        if liquidity.fungible_amount <= Amount::ZERO {
            return Ok(());
        }

        self.initial_liquidity.set(Some(liquidity.clone()));

        let swap_application_id = self.swap_application_id.get().unwrap();
        let spender = Account {
            chain_id: swap_creator_chain_id,
            owner: AccountOwner::from(swap_application_id),
        };
        self.approve(
            self.holder.get().unwrap(),
            spender,
            liquidity.fungible_amount,
        )
        .await
    }

    fn instantiate(
        &mut self,
        owner: Account,
        application: Account,
        mut argument: InstantiationArgument,
        enable_mining: bool,
        mining_supply: Option<Amount>,
        now: Timestamp,
    ) -> Result<(), StateError> {
        assert!(
            argument.meme.initial_supply > Amount::ZERO,
            "Invalid initial supply"
        );

        self.initial_owner_balance.set(Amount::from_tokens(100));

        self.swap_application_id.set(argument.swap_application_id);
        self.balances
            .insert(&application, argument.meme.initial_supply)?;
        self.holder.set(Some(application));
        self.owner.set(Some(owner));

        argument.meme.total_supply = argument.meme.initial_supply;
        self.meme.set(Some(argument.meme.clone()));

        self.blob_gateway_application_id
            .set(argument.blob_gateway_application_id);
        self.ams_application_id.set(argument.ams_application_id);
        self.proxy_application_id.set(argument.proxy_application_id);

        if enable_mining {
            self.initialize_mining_info(mining_supply.unwrap_or(argument.meme.total_supply), now);
        }

        Ok(())
    }

    async fn mint(&mut self, to: Account, amount: Amount) -> Result<(), StateError> {
        self.transfer(self.holder.get().unwrap(), to, amount).await
    }

    fn proxy_application_id(&self) -> Option<ApplicationId> {
        *self.proxy_application_id.get()
    }

    fn blob_gateway_application_id(&self) -> Option<ApplicationId> {
        *self.blob_gateway_application_id.get()
    }

    fn ams_application_id(&self) -> Option<ApplicationId> {
        *self.ams_application_id.get()
    }

    fn swap_application_id(&self) -> Option<ApplicationId> {
        *self.swap_application_id.get()
    }

    async fn transfer_(
        &mut self,
        from: Account,
        to: Account,
        amount: Amount,
    ) -> Result<(), StateError> {
        let from_balance = self.balances.get(&from).await?.unwrap();

        let to_balance = if let Some(balance) = self.balances.get(&to).await? {
            balance.try_add(amount)?
        } else {
            amount
        };

        self.balances.insert(&from, from_balance.try_sub(amount)?)?;
        Ok(self.balances.insert(&to, to_balance)?)
    }

    async fn transfer(
        &mut self,
        from: Account,
        to: Account,
        amount: Amount,
    ) -> Result<(), StateError> {
        assert!(amount > Amount::ZERO, "Invalid amount");
        assert!(from != to, "Self transfer");

        let from_balance = self.balances.get(&from).await?.unwrap_or(Amount::ZERO);

        assert!(
            from_balance >= amount,
            "Insufficient balance: from {} balance {} < amount {}",
            from,
            from_balance,
            amount
        );

        self.transfer_(from, to, amount).await
    }

    async fn transfer_ensure(
        &mut self,
        from: Account,
        to: Account,
        amount: Amount,
    ) -> Result<(), StateError> {
        ensure!(amount > Amount::ZERO, StateError::InvalidAmount);
        ensure!(from != to, StateError::SelfTransfer);

        let from_balance = self.balances.get(&from).await?.unwrap();

        log::debug!(
            "Transfer {} tokens from {} balance {} to {}",
            amount,
            from,
            from_balance,
            to
        );
        ensure!(from_balance >= amount, StateError::InsufficientFunds);

        self.transfer_(from, to, amount).await
    }

    async fn approve(
        &mut self,
        owner: Account,
        spender: Account,
        amount: Amount,
    ) -> Result<(), StateError> {
        // Self approve is not allowed
        if owner == spender {
            return Err(StateError::InvalidOwner);
        }
        // Approve application balance to meme creator is not allowed
        if owner == self.holder.get().unwrap() && spender == self.owner.get().unwrap() {
            return Err(StateError::InvalidOwner);
        }

        let owner_balance = self.balance_of(owner).await;
        if owner_balance < amount {
            return Err(StateError::InsufficientFunds);
        }

        let mut allowances: HashMap<Account, Amount> =
            if let Some(_allowances) = self.allowances.get(&owner).await? {
                _allowances
            } else {
                HashMap::new()
            };

        let spender_allowance = if let Some(allowance) = allowances.get(&spender) {
            allowance.try_add(amount)?
        } else {
            amount
        };

        self.balances
            .insert(&owner, owner_balance.try_sub(amount)?)?;

        allowances.insert(spender, spender_allowance);
        Ok(self.allowances.insert(&owner, allowances)?)
    }

    async fn transfer_from(
        &mut self,
        owner: Account,
        from: Account,
        to: Account,
        amount: Amount,
    ) -> Result<(), StateError> {
        let Some(mut allowances) = self.allowances.get(&from).await? else {
            panic!("Invalid from");
        };
        let Some(&allowance) = allowances.get(&owner) else {
            panic!("Invalid owner");
        };
        assert!(allowance >= amount, "Insufficient allowance");
        let balance = match self.balances.get(&to).await? {
            Some(balance) => balance.try_add(amount)?,
            _ => amount,
        };
        self.balances.insert(&to, balance)?;
        allowances.insert(owner, allowance.try_sub(amount)?);
        Ok(self.allowances.insert(&from, allowances)?)
    }

    fn owner(&self) -> Account {
        self.owner.get().unwrap()
    }

    fn owner_signer(&self) -> AccountOwner {
        self.owner.get().unwrap().owner
    }

    async fn balance_of(&self, owner: Account) -> Amount {
        match self.balances.get(&owner).await.unwrap() {
            Some(amount) => amount,
            _ => Amount::ZERO,
        }
    }

    async fn allowance_of(&self, owner: Account, spender: Account) -> Amount {
        match self.allowances.get(&owner).await.unwrap() {
            Some(allowances) => match allowances.get(&spender) {
                Some(&amount) => amount,
                _ => Amount::ZERO,
            },
            _ => Amount::ZERO,
        }
    }

    fn initial_owner_balance(&self) -> Amount {
        *self.initial_owner_balance.get()
    }

    fn transfer_ownership(&mut self, owner: Account, new_owner: Account) -> Result<(), StateError> {
        assert!(owner == self.owner.get().unwrap(), "Invalid owner");
        self.owner.set(Some(new_owner));
        Ok(())
    }

    fn name(&self) -> String {
        self.meme.get().as_ref().unwrap().name.clone()
    }

    fn logo_store_type(&self) -> StoreType {
        self.meme
            .get()
            .as_ref()
            .unwrap()
            .metadata
            .logo_store_type
            .clone()
    }

    fn logo(&self) -> CryptoHash {
        self.meme.get().as_ref().unwrap().metadata.logo.unwrap()
    }

    fn description(&self) -> String {
        self.meme
            .get()
            .as_ref()
            .unwrap()
            .metadata
            .description
            .clone()
    }

    fn twitter(&self) -> Option<String> {
        self.meme.get().as_ref().unwrap().metadata.twitter.clone()
    }

    fn telegram(&self) -> Option<String> {
        self.meme.get().as_ref().unwrap().metadata.telegram.clone()
    }

    fn discord(&self) -> Option<String> {
        self.meme.get().as_ref().unwrap().metadata.discord.clone()
    }

    fn website(&self) -> Option<String> {
        self.meme.get().as_ref().unwrap().metadata.website.clone()
    }

    fn github(&self) -> Option<String> {
        self.meme.get().as_ref().unwrap().metadata.github.clone()
    }

    fn meme(&self) -> Meme {
        self.meme.get().as_ref().unwrap().clone()
    }

    fn mining_target(&self) -> CryptoHash {
        self.mining_info.get().as_ref().unwrap().target
    }

    fn previous_nonce(&self) -> CryptoHash {
        self.mining_info.get().as_ref().unwrap().previous_nonce
    }

    fn mining_height(&self) -> BlockHeight {
        self.mining_info.get().as_ref().unwrap().mining_height
    }

    fn mining_info(&self) -> MiningInfo {
        self.mining_info.get().as_ref().unwrap().clone()
    }

    fn maybe_mining_info(&self) -> Option<MiningInfo> {
        self.mining_info.get().clone()
    }

    fn update_mining_info(&mut self, info: MiningInfo) {
        self.mining_info.set(Some(info));
    }

    fn is_mining_started(&self) -> bool {
        self.mining_info
            .get()
            .as_ref()
            .map_or(false, |info| info.mining_started)
    }

    fn start_mining(&mut self) {
        if let Some(mining_info) = &mut self.mining_info.get() {
            let _mining_info = MiningInfo {
                mining_started: true,
                ..mining_info.clone()
            };
            self.update_mining_info(_mining_info);
        }
    }

    async fn mining_reward(&mut self, owner: Account, now: Timestamp) -> Result<(), StateError> {
        let reward_amount = self.mining_reward_amount();
        self.mint(owner, reward_amount).await?;

        // Update mining info
        let mut mining_info = self.mining_info();
        mining_info.try_half(now);
        self.update_mining_info(mining_info);

        Ok(())
    }
}
