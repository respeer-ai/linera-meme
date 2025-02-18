// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

use linera_sdk::{
    base::{BytecodeId, Owner},
    views::{linera_views, MapView, RegisterView, RootView, ViewStorageContext},
};
use proxy::InstantiationArgument;

/// The application state.
#[derive(RootView)]
#[view(context = "ViewStorageContext")]
pub struct ProxyState {
    pub meme_bytecode_id: RegisterView<Option<BytecodeId>>,
    pub operators: MapView<Owner, bool>,
}

#[allow(dead_code)]
impl ProxyState {
    pub(crate) async fn initantiate(&mut self, argument: InstantiationArgument, owner: Owner) {
        self.operators
            .insert(&owner, false)
            .expect("Failed insert operator");
        self.meme_bytecode_id.set(Some(argument.meme_bytecode_id));
    }
}
