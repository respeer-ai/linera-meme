// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

use abi::meme::{InstantiationArgument, Meme, Mint};
use linera_sdk::{
    base::{AccountOwner, Amount, ApplicationId},
    views::{linera_views, MapView, RegisterView, RootView, ViewStorageContext},
};
use std::collections::HashMap;

/// The application state.
#[derive(RootView)]
#[view(context = "ViewStorageContext")]
pub struct MemeState {
    // Meme metadata
    pub meme: RegisterView<Option<Meme>>,
    pub mint: RegisterView<Option<Mint>>,
    pub fee_percent: RegisterView<Option<Amount>>,
    pub blob_gateway_application_id: RegisterView<Option<ApplicationId>>,
    pub ams_application_id: RegisterView<Option<ApplicationId>>,
    pub swap_application_id: RegisterView<Option<ApplicationId>>,

    // Account information
    pub balances: MapView<AccountOwner, Amount>,
    pub allowances: MapView<AccountOwner, HashMap<AccountOwner, Amount>>,
    pub locked_allowances: MapView<AccountOwner, Amount>,
}

#[allow(dead_code)]
impl MemeState {
    pub(crate) async fn instantiate(&mut self, argument: InstantiationArgument) {
        self.meme.set(Some(argument.meme));
        self.mint.set(argument.mint);
        self.fee_percent.set(argument.fee_percent);
        self.blob_gateway_application_id
            .set(argument.blob_gateway_application_id);
        self.ams_application_id.set(argument.ams_application_id);
        self.swap_application_id.set(argument.swap_application_id);
    }
}
