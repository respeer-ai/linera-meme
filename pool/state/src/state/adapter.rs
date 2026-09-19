use std::{cell::RefCell, rc::Rc};

use abi::pool::state_v1::StateInstantiationArgument;
use abi::pool::{Pool, Transaction};
use async_trait::async_trait;
use linera_sdk::linera_base_types::{Account, Amount, ApplicationId};

use crate::{interfaces::state::StateInterface, state::PoolState};

pub struct StateAdapter {
    state: Rc<RefCell<PoolState>>,
}

impl StateAdapter {
    pub fn new(state: Rc<RefCell<PoolState>>) -> Self {
        Self { state }
    }
}

#[async_trait(?Send)]
impl StateInterface for StateAdapter {
    type Error = <PoolState as StateInterface>::Error;

    fn instantiate(&mut self, argument: StateInstantiationArgument) -> Result<(), Self::Error> {
        self.state.borrow_mut().instantiate(argument)?;
        Ok(())
    }

    async fn business_application_id(&mut self) -> Result<ApplicationId, Self::Error> {
        self.state.borrow_mut().business_application_id().await
    }

    async fn handoff(
        &mut self,
        new_business_application_id: ApplicationId,
    ) -> Result<(), Self::Error> {
        self.state
            .borrow_mut()
            .handoff(new_business_application_id)
            .await
    }

    async fn operator(&mut self) -> Result<Account, Self::Error> {
        self.state.borrow_mut().operator().await
    }

    async fn set_operator(&mut self, new_operator: Account) -> Result<(), Self::Error> {
        self.state.borrow_mut().set_operator(new_operator).await
    }

    async fn initialize(
        &mut self,
        pool: Pool,
        router_application_id: ApplicationId,
    ) -> Result<(), Self::Error> {
        self.state
            .borrow_mut()
            .initialize(pool, router_application_id)
            .await
    }

    async fn set_pool(&mut self, pool: Pool) -> Result<(), Self::Error> {
        self.state.borrow_mut().set_pool(pool).await
    }

    async fn pool(&self) -> Result<Pool, Self::Error> {
        self.state.borrow().pool().await
    }

    async fn router_application_id(&self) -> Result<ApplicationId, Self::Error> {
        self.state.borrow().router_application_id().await
    }

    async fn total_supply(&self) -> Result<Amount, Self::Error> {
        self.state.borrow().total_supply().await
    }

    async fn mint_shares(&mut self, to: Account, amount: Amount) -> Result<(), Self::Error> {
        self.state.borrow_mut().mint_shares(to, amount).await
    }

    async fn burn_shares(&mut self, from: Account, amount: Amount) -> Result<(), Self::Error> {
        self.state.borrow_mut().burn_shares(from, amount).await
    }

    async fn liquidity(&self, account: Account) -> Result<Amount, Self::Error> {
        self.state.borrow().liquidity(account).await
    }

    async fn claimable_balance(
        &self,
        token: Option<ApplicationId>,
        owner: Account,
    ) -> Result<Amount, Self::Error> {
        self.state.borrow().claimable_balance(token, owner).await
    }

    async fn claiming_balance(
        &self,
        token: Option<ApplicationId>,
        owner: Account,
    ) -> Result<Amount, Self::Error> {
        self.state.borrow().claiming_balance(token, owner).await
    }

    async fn credit_claimable(
        &mut self,
        token: Option<ApplicationId>,
        owner: Account,
        amount: Amount,
    ) -> Result<(), Self::Error> {
        self.state
            .borrow_mut()
            .credit_claimable(token, owner, amount)
            .await
    }

    async fn debit_claimable(
        &mut self,
        token: Option<ApplicationId>,
        owner: Account,
        amount: Amount,
    ) -> Result<(), Self::Error> {
        self.state
            .borrow_mut()
            .debit_claimable(token, owner, amount)
            .await
    }

    async fn claim(
        &mut self,
        token: Option<ApplicationId>,
        owner: Account,
        amount: Amount,
    ) -> Result<(), Self::Error> {
        self.state.borrow_mut().claim(token, owner, amount).await
    }

    async fn claim_success(
        &mut self,
        token: Option<ApplicationId>,
        owner: Account,
        amount: Amount,
    ) -> Result<(), Self::Error> {
        self.state
            .borrow_mut()
            .claim_success(token, owner, amount)
            .await
    }

    async fn claim_fail(
        &mut self,
        token: Option<ApplicationId>,
        owner: Account,
        amount: Amount,
    ) -> Result<(), Self::Error> {
        self.state
            .borrow_mut()
            .claim_fail(token, owner, amount)
            .await
    }

    async fn set_fee_to(
        &mut self,
        operator: Account,
        account: Account,
    ) -> Result<(), Self::Error> {
        self.state.borrow_mut().set_fee_to(operator, account).await
    }

    async fn set_fee_to_setter(
        &mut self,
        operator: Account,
        account: Account,
    ) -> Result<(), Self::Error> {
        self.state
            .borrow_mut()
            .set_fee_to_setter(operator, account)
            .await
    }

    async fn build_transaction(
        &mut self,
        transaction: Transaction,
    ) -> Result<Transaction, Self::Error> {
        self.state.borrow_mut().build_transaction(transaction).await
    }
}
