// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

use linera_sdk::{
    base::{BytecodeId, Owner},
    views::{linera_views, MapView, RegisterView, RootView, ViewStorageContext},
};
use proxy::{InstantiationArgument, ProxyError};

/// The application state.
#[derive(RootView)]
#[view(context = "ViewStorageContext")]
pub struct ProxyState {
    pub meme_bytecode_id: RegisterView<Option<BytecodeId>>,
    /// Operator and banned
    pub operators: MapView<Owner, bool>,
    /// Genesis miner and approvals it should get
    pub genesis_miners: MapView<Owner, usize>,
    /// Miners and mining chains (ignore permissionless chain)
    pub miners: MapView<Owner, u32>,
}

#[allow(dead_code)]
impl ProxyState {
    pub(crate) async fn initantiate(
        &mut self,
        argument: InstantiationArgument,
        owner: Owner,
    ) -> Result<(), ProxyError> {
        self.meme_bytecode_id.set(Some(argument.meme_bytecode_id));
        Ok(self.operators.insert(&owner, false)?)
    }

    pub(crate) async fn add_genesis_miner(&mut self, owner: Owner) -> Result<(), ProxyError> {
        if !self.genesis_miners.contains_key(&owner).await? {
            let operators = self.operators.count().await?;
            let approvals = std::cmp::max(operators * 2 / 3, 1);
            return Ok(self.genesis_miners.insert(&owner, approvals)?);
        }
        Ok(())
    }
}
