// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

use abi::meme::{InstantiationArgument, Liquidity, Meme};
use linera_sdk::{
    base::{AccountOwner, Amount, ApplicationId, Owner},
    views::{linera_views, MapView, RegisterView, RootView, ViewStorageContext},
};
use meme::MemeError;
use std::collections::HashMap;

/// The application state.
#[derive(RootView)]
#[view(context = "ViewStorageContext")]
pub struct MemeState {
    pub owner: RegisterView<Option<Owner>>,
    pub holder: RegisterView<Option<AccountOwner>>,

    // Meme metadata
    pub meme: RegisterView<Option<Meme>>,
    pub initial_liquidity: RegisterView<Option<Liquidity>>,

    pub blob_gateway_application_id: RegisterView<Option<ApplicationId>>,
    pub ams_application_id: RegisterView<Option<ApplicationId>>,
    pub proxy_application_id: RegisterView<Option<ApplicationId>>,
    pub swap_application_id: RegisterView<Option<ApplicationId>>,
    pub virtual_initial_liquidity: RegisterView<bool>,

    // Account information
    pub balances: MapView<AccountOwner, Amount>,
    pub allowances: MapView<AccountOwner, HashMap<AccountOwner, Amount>>,
}

/// Created meme token will be added to liquidity pool directly

#[allow(dead_code)]
impl MemeState {
    async fn initialize_liquidity(&mut self, liquidity: Liquidity) -> Result<(), MemeError> {
        assert!(
            liquidity.fungible_amount >= Amount::ZERO,
            "Invalid initial liquidity"
        );
        assert!(
            liquidity.native_amount >= Amount::ZERO,
            "Invalid initial liquidity"
        );

        self.initial_liquidity.set(Some(liquidity.clone()));

        let spender = AccountOwner::Application(self.swap_application_id.get().unwrap());
        self.approve(
            self.holder.get().unwrap(),
            spender,
            liquidity.fungible_amount,
        )
        .await
    }

    pub(crate) async fn instantiate(
        &mut self,
        owner: Owner,
        application: AccountOwner,
        mut argument: InstantiationArgument,
    ) -> Result<(), MemeError> {
        assert!(
            argument.meme.initial_supply > Amount::ZERO,
            "Invalid initial supply"
        );

        self.swap_application_id.set(argument.swap_application_id);
        self.balances
            .insert(&application, argument.meme.initial_supply)?;
        self.holder.set(Some(application));
        self.owner.set(Some(owner));

        if let Some(liquidity) = argument.initial_liquidity {
            assert!(
                argument.meme.initial_supply >= liquidity.fungible_amount,
                "Invalid initial supply"
            );
            self.initialize_liquidity(liquidity).await?;
        }

        argument.meme.total_supply = argument.meme.initial_supply;
        self.meme.set(Some(argument.meme.clone()));

        self.blob_gateway_application_id
            .set(argument.blob_gateway_application_id);
        self.ams_application_id.set(argument.ams_application_id);
        self.proxy_application_id.set(argument.proxy_application_id);
        self.virtual_initial_liquidity
            .set(argument.virtual_initial_liquidity);

        Ok(())
    }

    pub(crate) async fn initialize_balance(
        &mut self,
        owner: AccountOwner,
        amount: Amount,
    ) -> Result<(), MemeError> {
        let holder = self.holder.get().unwrap();
        let balance = self.balances.get(&holder).await?.unwrap();
        assert!(balance >= amount, "Insufficient balance");
        self.balances.insert(&holder, balance)?;
        Ok(self.balances.insert(&owner, amount)?)
    }

    pub(crate) async fn proxy_application_id(&self) -> Option<ApplicationId> {
        *self.proxy_application_id.get()
    }

    pub(crate) async fn blob_gateway_application_id(&self) -> Option<ApplicationId> {
        *self.blob_gateway_application_id.get()
    }

    pub(crate) async fn ams_application_id(&self) -> Option<ApplicationId> {
        *self.ams_application_id.get()
    }

    pub(crate) async fn swap_application_id(&self) -> Option<ApplicationId> {
        *self.swap_application_id.get()
    }

    pub(crate) async fn transfer(
        &mut self,
        from: AccountOwner,
        to: AccountOwner,
        amount: Amount,
    ) -> Result<(), MemeError> {
        assert!(amount > Amount::ZERO, "Invalid amount");
        assert!(from != to, "Self transfer");

        let from_balance = self.balances.get(&from).await?.unwrap();

        assert!(from_balance >= amount, "Insufficient balance");

        let to_balance = if let Some(balance) = self.balances.get(&to).await? {
            balance.try_add(amount)?
        } else {
            amount
        };

        self.balances.insert(&from, from_balance.try_sub(amount)?)?;
        Ok(self.balances.insert(&to, to_balance)?)
    }

    pub(crate) async fn approve(
        &mut self,
        owner: AccountOwner,
        spender: AccountOwner,
        amount: Amount,
    ) -> Result<(), MemeError> {
        // Self approve is not allowed
        if owner == spender {
            return Err(MemeError::InvalidOwner);
        }
        // Approve application balance to meme creator is not allowed
        if owner == self.holder.get().unwrap()
            && spender == AccountOwner::User(self.owner.get().unwrap())
        {
            return Err(MemeError::InvalidOwner);
        }

        let owner_balance = self.balance_of(owner).await;
        if owner_balance < amount {
            return Err(MemeError::InsufficientFunds);
        }

        let mut allowances = if let Some(_allowances) = self.allowances.get(&owner).await? {
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

    pub(crate) async fn owner(&mut self) -> Owner {
        self.owner.get().unwrap()
    }

    pub(crate) async fn balance_of(&self, owner: AccountOwner) -> Amount {
        match self.balances.get(&owner).await.unwrap() {
            Some(amount) => amount,
            _ => Amount::ZERO,
        }
    }

    pub(crate) async fn allowance_of(&self, owner: AccountOwner, spender: AccountOwner) -> Amount {
        match self.allowances.get(&owner).await.unwrap() {
            Some(allowances) => match allowances.get(&spender) {
                Some(&amount) => amount,
                _ => Amount::ZERO,
            },
            _ => Amount::ZERO,
        }
    }

    pub(crate) async fn virtual_initial_liquidity(&self) -> bool {
        *self.virtual_initial_liquidity.get()
    }

    pub(crate) async fn initial_liquidity(&self) -> Option<Liquidity> {
        self.initial_liquidity.get().clone()
    }
}
