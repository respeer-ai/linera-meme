// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

use abi::meme::{InstantiationArgument, Meme};
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

    // Meme metadata
    pub meme: RegisterView<Option<Meme>>,

    pub blob_gateway_application_id: RegisterView<Option<ApplicationId>>,
    pub ams_application_id: RegisterView<Option<ApplicationId>>,
    pub swap_application_id: RegisterView<Option<ApplicationId>>,
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
        assert!(
            argument.swap_application_id.is_some(),
            "Invalid swap application"
        );

        let initial_supply = argument.meme.initial_supply;
        argument.meme.total_supply = argument.meme.initial_supply;

        self.meme.set(Some(argument.meme.clone()));

        self.blob_gateway_application_id
            .set(argument.blob_gateway_application_id);
        self.ams_application_id.set(argument.ams_application_id);
        self.swap_application_id.set(argument.swap_application_id);
        self.proxy_application_id.set(argument.proxy_application_id);

        self.balances.insert(
            &application,
            argument
                .meme
                .initial_supply
                .try_sub(argument.initial_liquidity.fungible_amount)?,
        )?;
        let swap_application = AccountOwner::Application(argument.swap_application_id.unwrap());
        self.allowances.insert(
            &application,
            HashMap::from([(swap_application, argument.initial_liquidity.fungible_amount)]),
        )?;

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

    pub(crate) async fn swap_application_id(&self) -> Option<ApplicationId> {
        *self.swap_application_id.get()
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
}
