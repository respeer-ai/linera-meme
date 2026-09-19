use crate::{
    interfaces::state::StateInterface,
    state::{errors::StateError, PoolState},
};
use abi::meme_token::MemeToken;
use abi::pool::state_v1::StateInstantiationArgument;
use abi::pool::{Pool, Transaction};
use async_trait::async_trait;
use linera_sdk::linera_base_types::{Account, Amount, ApplicationId};

#[async_trait(?Send)]
impl StateInterface for PoolState {
    type Error = StateError;

    fn instantiate(&mut self, argument: StateInstantiationArgument) -> Result<(), StateError> {
        self.business_application_id
            .set(Some(argument.business_application_id));
        self.operator.set(argument.operator);

        Ok(())
    }

    async fn business_application_id(&mut self) -> Result<ApplicationId, StateError> {
        self.business_application_id
            .get()
            .ok_or(StateError::BusinessApplicationIdNotInitialized)
    }

    async fn handoff(
        &mut self,
        new_business_application_id: ApplicationId,
    ) -> Result<(), StateError> {
        self.business_application_id
            .set(Some(new_business_application_id));
        Ok(())
    }

    async fn operator(&mut self) -> Result<Account, StateError> {
        self.operator.get().ok_or(StateError::OperatorNotInitialized)
    }

    async fn set_operator(&mut self, new_operator: Account) -> Result<(), StateError> {
        self.operator.set(Some(new_operator));
        Ok(())
    }

    async fn initialize(
        &mut self,
        pool: Pool,
        router_application_id: ApplicationId,
    ) -> Result<(), StateError> {
        if self.pool.get().is_some() {
            return Err(StateError::AlreadyInitialized);
        }

        self.pool.set(Some(pool));
        self.router_application_id
            .set(Some(router_application_id));
        self.transaction_id.set(1000);

        Ok(())
    }

    async fn set_pool(&mut self, pool: Pool) -> Result<(), StateError> {
        if self.pool.get().is_none() {
            return Err(StateError::PoolNotInitialized);
        }
        self.pool.set(Some(pool));
        Ok(())
    }

    async fn pool(&self) -> Result<Pool, StateError> {
        self.pool.get().clone().ok_or(StateError::PoolNotInitialized)
    }

    async fn router_application_id(&self) -> Result<ApplicationId, StateError> {
        self.router_application_id
            .get()
            .ok_or(StateError::PoolNotInitialized)
    }

    async fn total_supply(&self) -> Result<Amount, StateError> {
        Ok(*self.total_supply.get())
    }

    async fn mint_shares(&mut self, to: Account, amount: Amount) -> Result<(), StateError> {
        self.total_supply
            .set(self.total_supply.get().try_add(amount)?);

        let share = self.liquidity(to).await?;
        self.shares.insert(&to, share.try_add(amount)?)?;
        Ok(())
    }

    async fn burn_shares(&mut self, from: Account, amount: Amount) -> Result<(), StateError> {
        self.total_supply
            .set(self.total_supply.get().try_sub(amount)?);

        let share = self.liquidity(from).await?;
        assert!(amount <= share, "Invalid liquidity");

        self.shares.insert(&from, share.try_sub(amount)?)?;
        Ok(())
    }

    async fn liquidity(&self, account: Account) -> Result<Amount, StateError> {
        Ok(self.shares.get(&account).await?.unwrap_or(Amount::ZERO))
    }

    async fn claimable_balance(
        &self,
        token: Option<ApplicationId>,
        owner: Account,
    ) -> Result<Amount, StateError> {
        let token = MemeToken::from(token);
        Ok(self
            .claimable_balances
            .get(&token)
            .await?
            .and_then(|balances| balances.get(&owner).copied())
            .unwrap_or(Amount::ZERO))
    }

    async fn claiming_balance(
        &self,
        token: Option<ApplicationId>,
        owner: Account,
    ) -> Result<Amount, StateError> {
        let token = MemeToken::from(token);
        Ok(self
            .claiming_balances
            .get(&token)
            .await?
            .and_then(|balances| balances.get(&owner).copied())
            .unwrap_or(Amount::ZERO))
    }

    async fn credit_claimable(
        &mut self,
        token: Option<ApplicationId>,
        owner: Account,
        amount: Amount,
    ) -> Result<(), StateError> {
        assert!(amount > Amount::ZERO, "Invalid amount");

        let token = MemeToken::from(token);
        let mut balances = self.claimable_balances.get(&token).await?.unwrap_or_default();
        let current = balances.get(&owner).copied().unwrap_or(Amount::ZERO);
        balances.insert(owner, current.try_add(amount)?);
        self.claimable_balances.insert(&token, balances)?;
        Ok(())
    }

    async fn debit_claimable(
        &mut self,
        token: Option<ApplicationId>,
        owner: Account,
        amount: Amount,
    ) -> Result<(), StateError> {
        assert!(amount > Amount::ZERO, "Invalid amount");

        let token = MemeToken::from(token);
        let mut balances = self.claimable_balances.get(&token).await?.unwrap_or_default();
        let current = balances.get(&owner).copied().unwrap_or(Amount::ZERO);
        assert!(current >= amount, "Insufficient claimable balance");

        let next = current.try_sub(amount)?;
        if next == Amount::ZERO {
            balances.remove(&owner);
        } else {
            balances.insert(owner, next);
        }
        self.claimable_balances.insert(&token, balances)?;
        Ok(())
    }

    async fn claim(
        &mut self,
        token: Option<ApplicationId>,
        owner: Account,
        amount: Amount,
    ) -> Result<(), StateError> {
        self.debit_claimable(token, owner, amount).await?;

        let token = MemeToken::from(token);
        let mut balances = self
            .claiming_balances
            .get(&token)
            .await?
            .unwrap_or_default();
        let current = balances.get(&owner).copied().unwrap_or(Amount::ZERO);
        balances.insert(owner, current.try_add(amount)?);
        self.claiming_balances.insert(&token, balances)?;
        Ok(())
    }

    async fn claim_success(
        &mut self,
        token: Option<ApplicationId>,
        owner: Account,
        amount: Amount,
    ) -> Result<(), StateError> {
        assert!(amount > Amount::ZERO, "Invalid amount");

        let token = MemeToken::from(token);
        let mut balances = self
            .claiming_balances
            .get(&token)
            .await?
            .unwrap_or_default();
        let current = balances.get(&owner).copied().unwrap_or(Amount::ZERO);
        assert!(current >= amount, "Insufficient claiming balance");

        let next = current.try_sub(amount)?;
        if next == Amount::ZERO {
            balances.remove(&owner);
        } else {
            balances.insert(owner, next);
        }
        self.claiming_balances.insert(&token, balances)?;
        Ok(())
    }

    async fn claim_fail(
        &mut self,
        token: Option<ApplicationId>,
        owner: Account,
        amount: Amount,
    ) -> Result<(), StateError> {
        self.claim_success(token, owner, amount).await?;
        self.credit_claimable(token, owner, amount).await
    }

    async fn set_fee_to(
        &mut self,
        operator: Account,
        account: Account,
    ) -> Result<(), StateError> {
        let mut pool = self.pool().await?;

        assert!(pool.fee_to_setter == operator, "Invalid operator");
        pool.fee_to = account;

        self.pool.set(Some(pool));
        Ok(())
    }

    async fn set_fee_to_setter(
        &mut self,
        operator: Account,
        account: Account,
    ) -> Result<(), StateError> {
        let mut pool = self.pool().await?;

        assert!(pool.fee_to_setter == operator, "Invalid operator");
        pool.fee_to_setter = account;

        self.pool.set(Some(pool));
        Ok(())
    }

    async fn build_transaction(
        &mut self,
        mut transaction: Transaction,
    ) -> Result<Transaction, StateError> {
        let transaction_id = *self.transaction_id.get();
        self.transaction_id.set(transaction_id + 1);

        transaction.transaction_id = Some(transaction_id);
        Ok(transaction)
    }
}
