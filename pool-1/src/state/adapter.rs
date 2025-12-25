use std::{cell::RefCell, rc::Rc};

use super::errors::StateError;
use crate::{interfaces::state::StateInterface, state::PoolState, FundRequest};
use abi::swap::{
    pool::{InstantiationArgument, Pool, PoolParameters},
    transaction::Transaction,
};
use async_trait::async_trait;

use linera_sdk::linera_base_types::{Account, Amount, ApplicationId, ChainId, ModuleId, Timestamp};

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
    type Error = StateError;

    async fn instantiate(
        &mut self,
        argument: InstantiationArgument,
        parameters: PoolParameters,
        owner: Account,
        block_timestamp: Timestamp,
    ) -> Result<Amount, Self::Error> {
        self.state
            .borrow_mut()
            .instantiate(argument, parameters, owner, block_timestamp)
            .await
    }

    fn pool(&self) -> Pool {
        self.state.borrow().pool()
    }

    fn router_application_id(&self) -> ApplicationId {
        self.state.borrow().router_application_id()
    }

    fn reserve_0(&self) -> Amount {
        self.state.borrow().reserve_0()
    }

    fn reserve_1(&self) -> Amount {
        self.state.borrow().reserve_1()
    }

    fn consume_transfer_id(&mut self) -> u64 {
        self.state.borrow_mut().consume_transfer_id()
    }

    fn create_fund_request(&mut self, fund_request: FundRequest) -> Result<u64, Self::Error> {
        self.state.borrow_mut().create_fund_request(fund_request)
    }

    async fn fund_request(&self, transfer_id: u64) -> Result<FundRequest, Self::Error> {
        self.state.borrow().fund_request(transfer_id).await
    }

    async fn _fund_requests(&self) -> Result<Vec<FundRequest>, Self::Error> {
        self.state.borrow()._fund_requests().await
    }

    async fn update_fund_request(
        &mut self,
        transfer_id: u64,
        fund_request: FundRequest,
    ) -> Result<(), Self::Error> {
        self.state
            .borrow_mut()
            .update_fund_request(transfer_id, fund_request)
            .await
    }

    fn calculate_swap_amount_0(&self, amount_1: Amount) -> Result<Amount, Self::Error> {
        self.state.borrow().calculate_swap_amount_0(amount_1)
    }

    fn calculate_swap_amount_1(&self, amount_0: Amount) -> Result<Amount, Self::Error> {
        self.state.borrow().calculate_swap_amount_1(amount_0)
    }

    fn calculate_adjusted_amount_pair(
        &self,
        amount_0_out: Amount,
        amount_1_out: Amount,
    ) -> Result<(Amount, Amount), Self::Error> {
        self.state
            .borrow()
            .calculate_adjusted_amount_pair(amount_0_out, amount_1_out)
    }

    fn try_calculate_swap_amount_pair(
        &self,
        amount_0_desired: Amount,
        amount_1_desired: Amount,
        amount_0_min: Option<Amount>,
        amount_1_min: Option<Amount>,
    ) -> Result<(Amount, Amount), Self::Error> {
        self.state.borrow().try_calculate_swap_amount_pair(
            amount_0_desired,
            amount_1_desired,
            amount_0_min,
            amount_1_min,
        )
    }

    fn try_calculate_liquidity_amount_pair(
        &self,
        liquidity: Amount,
        amount_0_min: Option<Amount>,
        amount_1_min: Option<Amount>,
    ) -> Result<(Amount, Amount), Self::Error> {
        self.state.borrow().try_calculate_liquidity_amount_pair(
            liquidity,
            amount_0_min,
            amount_1_min,
        )
    }

    fn liquid(&mut self, balance_0: Amount, balance_1: Amount, block_timestamp: Timestamp) {
        self.state
            .borrow_mut()
            .liquid(balance_0, balance_1, block_timestamp)
    }

    async fn add_liquidity(
        &mut self,
        amount_0: Amount,
        amount_1: Amount,
        to: Account,
        block_timestamp: Timestamp,
    ) -> Result<Amount, Self::Error> {
        self.state
            .borrow_mut()
            .add_liquidity(amount_0, amount_1, to, block_timestamp)
            .await
    }

    async fn liquidity(&self, account: Account) -> Result<Amount, Self::Error> {
        self.state.borrow().liquidity(account).await
    }

    async fn mint(&mut self, to: Account, amount: Amount) -> Result<(), Self::Error> {
        self.state.borrow_mut().mint(to, amount).await
    }

    async fn burn(&mut self, from: Account, liquidity: Amount) -> Result<(), Self::Error> {
        self.state.borrow_mut().burn(from, liquidity).await
    }

    async fn mint_shares(
        &mut self,
        amount_0: Amount,
        amount_1: Amount,
        to: Account,
    ) -> Result<Amount, Self::Error> {
        self.state
            .borrow_mut()
            .mint_shares(amount_0, amount_1, to)
            .await
    }

    fn calculate_liquidity(&self, amount_0: Amount, amount_1: Amount) -> Amount {
        self.state.borrow().calculate_liquidity(amount_0, amount_1)
    }

    fn set_fee_to(&mut self, operator: Account, account: Account) {
        self.state.borrow_mut().set_fee_to(operator, account)
    }

    fn set_fee_to_setter(&mut self, operator: Account, account: Account) {
        self.state.borrow_mut().set_fee_to_setter(operator, account)
    }

    fn calculate_price_pair(&self) -> (Amount, Amount) {
        self.state.borrow().calculate_price_pair()
    }

    fn build_transaction(
        &self,
        owner: Account,
        amount_0_in: Option<Amount>,
        amount_1_in: Option<Amount>,
        amount_0_out: Option<Amount>,
        amount_1_out: Option<Amount>,
        liquidity: Option<Amount>,
        timestamp: Timestamp,
    ) -> Transaction {
        self.state.borrow().build_transaction(
            owner,
            amount_0_in,
            amount_1_in,
            amount_0_out,
            amount_1_out,
            liquidity,
            timestamp,
        )
    }

    fn create_transaction(&mut self, transaction: Transaction) -> Transaction {
        self.state.borrow_mut().create_transaction(transaction)
    }
}
