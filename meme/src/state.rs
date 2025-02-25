// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

use abi::meme::{InstantiationArgument, Meme, Mint};
use linera_sdk::{
    base::{Account, AccountOwner, Amount, ApplicationId, Owner},
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
    pub mint: RegisterView<Option<Mint>>,
    pub fee_percent: RegisterView<Option<Amount>>,

    pub blob_gateway_application_id: RegisterView<Option<ApplicationId>>,
    pub ams_application_id: RegisterView<Option<ApplicationId>>,
    pub swap_application_id: RegisterView<Option<ApplicationId>>,
    pub proxy_application_id: RegisterView<Option<ApplicationId>>,

    // Account information
    pub balances: MapView<AccountOwner, Amount>,
    pub allowances: MapView<AccountOwner, HashMap<AccountOwner, Amount>>,
}

/// If the owner would like to create pool of this token to swap fairly, it
/// should mint from the application balance then create

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
        let initial_supply = argument.meme.initial_supply;

        argument.meme.total_supply = argument.meme.initial_supply;

        self.meme.set(Some(argument.meme));
        self.mint.set(argument.mint);
        self.fee_percent.set(argument.fee_percent);

        self.blob_gateway_application_id
            .set(argument.blob_gateway_application_id);
        self.ams_application_id.set(argument.ams_application_id);
        self.swap_application_id.set(argument.swap_application_id);
        self.proxy_application_id.set(argument.proxy_application_id);

        self.balances.insert(&application, initial_supply)?;
        self.holder.set(Some(application));

        Ok(())
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

    async fn transfer(
        &mut self,
        from: AccountOwner,
        to: AccountOwner,
        amount: Amount,
    ) -> Result<(), MemeError> {
        assert!(amount > Amount::ZERO, "Invalid amount");

        let from_balance = self.balances.get(&from).await?.unwrap();

        assert!(from_balance >= amount, "Insufficient balance");

        let to_balance = if let Some(balance) = self.balances.get(&to).await? {
            balance.try_add(amount)?
        } else {
            amount
        };

        self.balances.insert(&from, from_balance.try_sub(amount)?)?;
        self.balances.insert(&to, to_balance)?;
        Ok(())
    }

    pub(crate) async fn mint(&mut self, to: AccountOwner, amount: Amount) -> Result<(), MemeError> {
        self.transfer(self.holder.get().unwrap(), to, amount).await
    }
}
