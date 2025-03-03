// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

use abi::swap::{
    router::{InstantiationArgument, Pool},
    transaction::Transaction,
};
use linera_sdk::{
    base::{ApplicationId, BytecodeId, ChainId, MessageId},
    views::{linera_views, MapView, QueueView, RegisterView, RootView, ViewStorageContext},
};
use std::collections::HashMap;
use swap::SwapError;

/// The application state.
#[derive(RootView)]
#[view(context = "ViewStorageContext")]
pub struct SwapState {
    pub meme_meme_pools: MapView<ApplicationId, HashMap<ApplicationId, Pool>>,
    pub meme_native_pools: MapView<ApplicationId, Pool>,

    pub pool_id: RegisterView<u64>,
    pub pool_meme_memes: MapView<u64, Vec<ApplicationId>>,
    pub pool_meme_natives: MapView<u64, ApplicationId>,

    pub last_transactions: QueueView<Transaction>,
    pub transaction_id: RegisterView<u64>,

    pub liquidity_rfq_bytecode_id: RegisterView<Option<BytecodeId>>,
    pub pool_bytecode_id: RegisterView<Option<BytecodeId>>,
}

#[allow(dead_code)]
impl SwapState {
    pub(crate) async fn instantiate(&mut self, argument: InstantiationArgument) {
        self.liquidity_rfq_bytecode_id
            .set(Some(argument.liquidity_rfq_bytecode_id));
        self.pool_bytecode_id.set(Some(argument.pool_bytecode_id));
        self.pool_id.set(1000);
    }

    pub(crate) async fn get_pool(
        &self,
        token_0: ApplicationId,
        token_1: Option<ApplicationId>,
    ) -> Result<Option<Pool>, SwapError> {
        match token_1 {
            Some(token_1) => match self.meme_meme_pools.get(&token_0).await? {
                Some(pools) => Ok(pools.get(&token_1).cloned()),
                _ => Ok(None),
            },
            _ => Ok(self.meme_native_pools.get(&token_0).await?),
        }
    }

    pub(crate) async fn get_pool_exchangable(
        &self,
        token_0: ApplicationId,
        token_1: Option<ApplicationId>,
    ) -> Result<Option<Pool>, SwapError> {
        if let Some(pool) = self.get_pool(token_0, token_1).await? {
            return Ok(Some(pool));
        }

        let Some(token_1) = token_1 else {
            return Ok(None);
        };

        self.get_pool(token_1, Some(token_0)).await
    }

    pub(crate) async fn liquidity_rfq_bytecode_id(&self) -> BytecodeId {
        self.liquidity_rfq_bytecode_id.get().unwrap()
    }

    pub(crate) async fn pool_bytecode_id(&self) -> BytecodeId {
        self.pool_bytecode_id.get().unwrap()
    }

    pub(crate) async fn create_pool(
        &mut self,
        token_0: ApplicationId,
        token_1: Option<ApplicationId>,
        pool_application: Account,
    ) -> Result<(), SwapError> {
        assert!(
            self.get_pool_exchangable(token_0, token_1) == None,
            "Pool exists"
        );

        let pool_id = self.pool_id.get();
        let pool = Pool {
            pool_id,
            token_0,
            token_1,
            pool_application,
        };

        if let Some(token_1) = token_1 {
            let mut pools = self.meme_meme_pools.get(&token_0).unwrap_or(HashMap::new());
            pools.insert(&token_1, pool);
            self.meme_meme_pools.insert(&token_0, pools)?;
            self.pool_meme_memes
                .insert(&pool_id, vec![token_0, token_1])?;
        } else {
            self.meme_native_pools.insert(&token_0, pools)?;
            self.pool_meme_natives.insert(&pool_id, token_0)?;
        }

        self.pool_id.set(pool_id + 1);
        Ok(())
    }
}
