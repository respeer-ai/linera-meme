// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

use abi::meme::{InstantiationArgument, Meme, Mint};
use linera_sdk::{
    base::{AccountOwner, Amount, ApplicationId, Owner},
    views::{linera_views, MapView, RegisterView, RootView, ViewStorageContext},
};
use std::collections::HashMap;

/// The application state.
#[derive(RootView)]
#[view(context = "ViewStorageContext")]
pub struct MemeState {
    pub owner: RegisterView<Option<Owner>>,

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
    pub locked_allowances: MapView<AccountOwner, Amount>,
}

#[allow(dead_code)]
impl MemeState {
    pub(crate) async fn instantiate(&mut self, owner: Owner, argument: InstantiationArgument) {
        self.owner.set(Some(owner));

        self.meme.set(Some(argument.meme));
        self.mint.set(argument.mint);
        self.fee_percent.set(argument.fee_percent);

        self.blob_gateway_application_id
            .set(argument.blob_gateway_application_id);
        self.ams_application_id.set(argument.ams_application_id);
        self.swap_application_id.set(argument.swap_application_id);
        self.proxy_application_id.set(argument.proxy_application_id);
    }

    pub(crate) async fn proxy_application_id(&self) -> ApplicationId {
        self.proxy_application_id.get().unwrap()
    }
}
