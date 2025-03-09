// Copyright (c) Zefchain Labs, Inc.
// SPDX-License-Identifier: Apache-2.0

use abi::swap::pool::{InstantiationArgument, Pool, PoolParameters};
use linera_sdk::{
    linera_base_types::{Account, ApplicationId, Timestamp},
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
            argument.pool_fee_percent,
            argument.protocol_fee_percent,
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
        self.pool.get().as_ref().unwrap().token_0
    }

    pub(crate) fn token_1(&self) -> Option<ApplicationId> {
        self.pool.get().as_ref().unwrap().token_1
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
    ) -> Result<(), PoolError> {
        let mut fund_request = self.fund_requests.get(&transfer_id).await?.unwrap();
        fund_request.status = status;
        Ok(self.fund_requests.insert(&transfer_id, fund_request)?)
    }
}
