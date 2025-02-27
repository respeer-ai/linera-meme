// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

use abi::meme::{InstantiationArgument, Meme};
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

    pub blob_gateway_application_id: RegisterView<Option<ApplicationId>>,
    pub ams_application_id: RegisterView<Option<ApplicationId>>,
    pub proxy_application_id: RegisterView<Option<ApplicationId>>,

    // Account information
    pub balances: MapView<AccountOwner, Amount>,
    pub allowances: MapView<AccountOwner, HashMap<AccountOwner, Amount>>,
}

/// Created meme token will be added to liquidity pool directly

#[allow(dead_code)]
impl MemeState {
    pub(crate) async fn instantiate(
        &mut self,
        owner: Owner,
        application: AccountOwner,
        mut argument: InstantiationArgument,
    ) -> Result<(), MemeError> {
        self.owner.set(Some(owner));

        assert!(
            argument.meme.initial_supply > Amount::ZERO,
            "Invalid initial supply"
        );
        assert!(
            argument.initial_liquidity.fungible_amount > Amount::ZERO,
            "Invalid initial liquidity"
        );
        assert!(
            argument.initial_liquidity.native_amount > Amount::ZERO,
            "Invalid initial liquidity"
        );
        assert!(
            argument.meme.initial_supply >= argument.initial_liquidity.fungible_amount,
            "Invalid initial supply"
        );

        argument.meme.total_supply = argument.meme.initial_supply;

        self.meme.set(Some(argument.meme.clone()));

        self.blob_gateway_application_id
            .set(argument.blob_gateway_application_id);
        self.ams_application_id.set(argument.ams_application_id);
        self.proxy_application_id.set(argument.proxy_application_id);

        self.balances
            .insert(&application, argument.meme.initial_supply)?;
        self.holder.set(Some(application));

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
        let owner_balance = self.balances.get(&owner).await?.expect("Invalid owner");
        assert!(owner_balance >= amount, "Insufficient balance");

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

        allowances.insert(spender, spender_allowance);
        Ok(self.allowances.insert(&owner, allowances)?)
    }
}
