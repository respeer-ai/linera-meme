// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

use abi::swap::pool::{InstantiationArgument, Pool, PoolParameters};
use linera_sdk::{
    linera_base_types::{Account, Amount, ApplicationId, Timestamp},
    views::{linera_views, MapView, RegisterView, RootView, ViewStorageContext},
};
use pool::{FundRequest, FundStatus, PoolError};

/// The application state.
#[derive(RootView)]
#[view(context = "ViewStorageContext")]
pub struct PoolState {
    pub pool: RegisterView<Option<Pool>>,
    pub router_application_id: RegisterView<Option<ApplicationId>>,

    pub transfer_id: RegisterView<u64>,
    pub fund_requests: MapView<u64, FundRequest>,
}

#[allow(dead_code)]
impl PoolState {
    pub(crate) fn instantiate(
        &mut self,
        argument: InstantiationArgument,
        parameters: PoolParameters,
        owner: Account,
        timestamp: Timestamp,
    ) {
        self.pool.set(Some(Pool::create(
            parameters.token_0,
            parameters.token_1,
            parameters.virtual_initial_liquidity,
            argument.amount_0,
            argument.amount_1,
            argument.pool_fee_percent_mul_100,
            argument.protocol_fee_percent_mul_100,
            owner,
            timestamp,
        )));
        self.router_application_id
            .set(Some(argument.router_application_id));
        self.transfer_id.set(1000);
    }

    pub(crate) fn pool(&self) -> Pool {
        self.pool.get().as_ref().unwrap().clone()
    }

    pub(crate) fn router_application_id(&self) -> ApplicationId {
        self.router_application_id.get().unwrap()
    }

    pub(crate) fn token_0(&self) -> ApplicationId {
        self.pool().token_0
    }

    pub(crate) fn token_1(&self) -> Option<ApplicationId> {
        self.pool().token_1
    }

    pub(crate) fn reserve_0(&self) -> Amount {
        self.pool().reserve_0
    }

    pub(crate) fn reserve_1(&self) -> Amount {
        self.pool().reserve_1
    }

    pub(crate) fn validate_token(&self, token: ApplicationId) {
        assert!(
            token == self.token_0()
                || (self.token_1().is_some() && token == self.token_1().unwrap()),
            "Invalid token"
        );
    }

    fn consume_transfer_id(&mut self) -> u64 {
        let transfer_id = *self.transfer_id.get();
        self.transfer_id.set(transfer_id + 1);
        transfer_id
    }

    pub(crate) fn create_fund_request(
        &mut self,
        fund_request: FundRequest,
    ) -> Result<u64, PoolError> {
        let transfer_id = self.consume_transfer_id();
        self.fund_requests.insert(&transfer_id, fund_request)?;
        Ok(transfer_id)
    }

    pub(crate) async fn fund_request(&self, transfer_id: u64) -> Result<FundRequest, PoolError> {
        Ok(self.fund_requests.get(&transfer_id).await?.unwrap())
    }

    pub(crate) async fn update_fund_request(
        &mut self,
        transfer_id: u64,
        status: FundStatus,
        error: Option<String>,
    ) -> Result<(), PoolError> {
        let mut fund_request = self.fund_requests.get(&transfer_id).await?.unwrap();
        fund_request.status = status;
        fund_request.error = error;
        Ok(self.fund_requests.insert(&transfer_id, fund_request)?)
    }

    pub(crate) fn calculate_swap_amount_0(&self, amount_1: Amount) -> Result<Amount, PoolError> {
        Ok(self.pool().calculate_swap_amount_0(amount_1)?)
    }

    pub(crate) fn calculate_swap_amount_1(&self, amount_0: Amount) -> Result<Amount, PoolError> {
        Ok(self.pool().calculate_swap_amount_1(amount_0)?)
    }

    pub(crate) fn calculate_adjusted_amount_pair(
        &self,
        amount_0_out: Amount,
        amount_1_out: Amount,
    ) -> Result<(Amount, Amount), PoolError> {
        Ok(self
            .pool()
            .calculate_adjusted_amount_pair(amount_0_out, amount_1_out)?)
    }

    pub(crate) fn try_calculate_swap_amount_pair(
        &self,
        amount_0_desired: Amount,
        amount_1_desired: Amount,
        amount_0_min: Option<Amount>,
        amount_1_min: Option<Amount>,
    ) -> Result<(Amount, Amount), PoolError> {
        Ok(self.pool().try_calculate_swap_amount_pair(
            amount_0_desired,
            amount_1_desired,
            amount_0_min,
            amount_1_min,
        )?)
    }

    pub(crate) fn liquid(
        &mut self,
        balance_0: Amount,
        balance_1: Amount,
        block_timestamp: Timestamp,
    ) {
        let mut pool: Pool = self.pool();
        pool.liquid(balance_0, balance_1, block_timestamp);
        self.pool.set(Some(pool));
    }

    pub(crate) fn add_liquidity(
        &mut self,
        amount_0: Amount,
        amount_1: Amount,
        to: Account,
        block_timestamp: Timestamp,
    ) {
        let mut pool: Pool = self.pool();

        pool.mint_shares(amount_0, amount_1, to);
        pool.liquid(
            pool.reserve_0.saturating_add(amount_0),
            pool.reserve_1.saturating_add(amount_1),
            block_timestamp,
        );
        self.pool.set(Some(pool));
    }
}
