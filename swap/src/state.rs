// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

use abi::swap::{
    router::{InstantiationArgument, Pool},
    transaction::Transaction,
};
use linera_sdk::{
    linera_base_types::{Account, Amount, ApplicationId, ChainId, MessageId, ModuleId},
    views::{linera_views, MapView, RegisterView, RootView, ViewStorageContext},
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
    // Token pair in the two elementes vec
    pub pool_meme_memes: MapView<u64, Vec<ApplicationId>>,
    pub pool_meme_natives: MapView<u64, ApplicationId>,

    pub pool_bytecode_id: RegisterView<Option<ModuleId>>,

    pub pool_chains: MapView<ChainId, MessageId>,
    pub token_creator_chain_ids: MapView<ApplicationId, ChainId>,
}

#[allow(dead_code)]
impl SwapState {
    pub(crate) async fn instantiate(&mut self, argument: InstantiationArgument) {
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

    pub(crate) async fn pool_bytecode_id(&self) -> ModuleId {
        self.pool_bytecode_id.get().unwrap()
    }

    pub(crate) async fn create_pool(
        &mut self,
        creator: Account,
        token_0: ApplicationId,
        token_1: Option<ApplicationId>,
        pool_application: Account,
    ) -> Result<(), SwapError> {
        assert!(
            self.get_pool_exchangable(token_0, token_1).await?.is_none(),
            "Pool exists"
        );

        let pool_id = self.pool_id.get();
        let pool = Pool {
            creator,
            pool_id: *pool_id,
            token_0,
            token_1,
            pool_application,
            latest_transaction: None,
            token_0_price: None,
            token_1_price: None,
        };

        if let Some(token_1) = token_1 {
            let mut pools = self
                .meme_meme_pools
                .get(&token_0)
                .await?
                .unwrap_or(HashMap::new());
            pools.insert(token_1, pool);
            self.meme_meme_pools.insert(&token_0, pools)?;
            self.pool_meme_memes
                .insert(&pool_id, vec![token_0, token_1])?;
        } else {
            self.meme_native_pools.insert(&token_0, pool)?;
            self.pool_meme_natives.insert(&pool_id, token_0)?;
        }

        self.pool_id.set(pool_id + 1);
        Ok(())
    }

    pub(crate) fn create_pool_chain(
        &mut self,
        chain_id: ChainId,
        message_id: MessageId,
    ) -> Result<(), SwapError> {
        Ok(self.pool_chains.insert(&chain_id, message_id)?)
    }

    pub(crate) fn create_token_creator_chain_id(
        &mut self,
        token: ApplicationId,
        chain_id: ChainId,
    ) -> Result<(), SwapError> {
        Ok(self.token_creator_chain_ids.insert(&token, chain_id)?)
    }

    pub(crate) async fn token_creator_chain_id(
        &self,
        token: ApplicationId,
    ) -> Result<ChainId, SwapError> {
        Ok(self.token_creator_chain_ids.get(&token).await?.unwrap())
    }

    pub(crate) async fn update_pool(
        &mut self,
        token_0: ApplicationId,
        token_1: Option<ApplicationId>,
        transaction: Transaction,
        token_0_price: Amount,
        token_1_price: Amount,
    ) -> Result<(), SwapError> {
        let Some(mut pool) = self.get_pool_exchangable(token_0, token_1).await? else {
            panic!("Invalid pool");
        };
        pool.latest_transaction = Some(transaction);
        pool.token_0_price = Some(token_0_price);
        pool.token_1_price = Some(token_1_price);

        if let Some(token_1) = token_1 {
            let mut pools = self
                .meme_meme_pools
                .get(&token_0)
                .await?
                .unwrap_or(HashMap::new());
            pools.insert(token_1, pool);
            self.meme_meme_pools.insert(&token_0, pools)?;
        } else {
            self.meme_native_pools.insert(&token_0, pool)?;
        }
        Ok(())
    }
}
