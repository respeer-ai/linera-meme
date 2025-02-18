// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

use abi::approval::Approval;
use linera_sdk::{
    base::{BytecodeId, Owner},
    views::{linera_views, MapView, RegisterView, RootView, ViewStorageContext},
};
use proxy::{InstantiationArgument, ProxyError};
use std::collections::HashMap;

/// The application state.
#[derive(RootView)]
#[view(context = "ViewStorageContext")]
pub struct ProxyState {
    pub meme_bytecode_id: RegisterView<Option<BytecodeId>>,
    /// Operator and banned
    pub operators: MapView<Owner, bool>,
    /// Genesis miner and approvals it should get
    pub genesis_miners: MapView<Owner, Approval>,
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
        self.operators.insert(&argument.operator, false)?;
        Ok(self.operators.insert(&owner, false)?)
    }

    pub(crate) async fn add_genesis_miner(&mut self, owner: Owner) -> Result<(), ProxyError> {
        if !self.genesis_miners.contains_key(&owner).await? {
            let operators = self.operators.count().await?;
            let approval = Approval {
                approvers: HashMap::new(),
                least_approvals: std::cmp::max(operators * 2 / 3, 1),
            };
            return Ok(self.genesis_miners.insert(&owner, approval)?);
        }
        Ok(())
    }

    pub(crate) async fn approve_genesis_miner(
        &mut self,
        owner: Owner,
        signer: Owner,
    ) -> Result<(), ProxyError> {
        let mut miner = self.genesis_miners.get(&owner).await.unwrap().unwrap();
        if miner.approvers.get(&signer).is_some() {
            return Ok(());
        }
        miner.approvers.insert(signer, true);
        Ok(self.genesis_miners.insert(&owner, miner)?)
    }
}
