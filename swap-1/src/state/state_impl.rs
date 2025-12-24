use crate::interfaces::state::StateInterface;
use crate::state::{errors::StateError, SwapState};
use abi::swap::{InstantiationArgument, Metadata, APPLICATION_TYPES, transaction::Transaction, router::Pool};
use async_trait::async_trait;
use linera_sdk::linera_base_types::{Account, Amount, ApplicationId, ChainId, Timestamp, ModuleId};

#[async_trait(?Send)]
impl StateInterface for SwapState {
    type Error = StateError;

    fn instantiate(&mut self, owner: Account, argument: InstantiationArgument) {
        self.pool_bytecode_id.set(Some(argument.pool_bytecode_id));
        self.pool_id.set(1000);
    }

    async fn get_pool(
        &self,
        token_0: ApplicationId,
        token_1: Option<ApplicationId>,
    ) -> Result<Option<Pool>, StateError> {
        match token_1 {
            Some(token_1) => Ok(self
                .meme_meme_pools
                .get(&token_0)
                .await?
                .and_then(|pools| pools.get(&token_1).cloned())),
            _ => Ok(self.meme_native_pools.get(&token_0).await?),
        }
    }

    async fn get_pool_exchangable(
        &self,
        token_0: ApplicationId,
        token_1: Option<ApplicationId>,
    ) -> Result<Option<Pool>, StateError> {
        if let Some(pool) = self.get_pool(token_0, token_1).await? {
            return Ok(Some(pool));
        }

        assert!(token_1.is_some(), "Invalid token pair");

        self.get_pool(token_1.unwrap(), Some(token_0)).await
    }

    fn pool_bytecode_id(&self) -> ModuleId {
        self.pool_bytecode_id
            .get()
            .expect("Not initialized pool_bytecode_id")
    }

    async fn create_pool(
        &mut self,
        creator: Account,
        token_0: ApplicationId,
        token_1: Option<ApplicationId>,
        pool_application: Account,
        timestamp: Timestamp,
    ) -> Result<(), StateError> {
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
            reserve_0: None,
            reserve_1: None,
            created_at: timestamp,
        };

        if let Some(token_1) = token_1 {
            let mut pools = self
                .meme_meme_pools
                .get(&token_0)
                .await?
                .unwrap_or_default();

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

    fn create_pool_chain(&mut self, chain_id: ChainId) -> Result<(), StateError> {
        self.pool_chains.insert(&chain_id, true)?;
        Ok(())
    }

    async fn update_pool(
        &mut self,
        token_0: ApplicationId,
        token_1: Option<ApplicationId>,
        transaction: Transaction,
        token_0_price: Amount,
        token_1_price: Amount,
        reserve_0: Amount,
        reserve_1: Amount,
    ) -> Result<(), StateError> {
        let Some(mut pool) = self.get_pool_exchangable(token_0, token_1).await? else {
            panic!("Invalid pool");
        };
        pool.latest_transaction = Some(transaction);
        pool.token_0_price = Some(token_0_price);
        pool.token_1_price = Some(token_1_price);
        pool.reserve_0 = Some(reserve_0);
        pool.reserve_1 = Some(reserve_1);

        if let Some(token_1) = token_1 {
            let mut pools = self
                .meme_meme_pools
                .get(&token_0)
                .await?
                .unwrap_or_default();

            pools.insert(token_1, pool);
            self.meme_meme_pools.insert(&token_0, pools)?;
        } else {
            self.meme_native_pools.insert(&token_0, pool)?;
        }
        Ok(())
    }
}
