use crate::{
    contract_inner::handlers::{
        request_meme_fund::RequestMemeFundHandler,
        transfer_meme_from_application::TransferMemeFromApplicationHandler,
    },
    interfaces::{parameters::ParametersInterface, state::StateInterface},
    FundRequest, FundStatus, FundType,
};
use abi::swap::pool::PoolMessage;
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::{Account, AccountOwner, Amount, ApplicationId};
use runtime::interfaces::{
    access_control::AccessControl, contract::ContractRuntimeContext, meme::MemeRuntimeContext,
};
use std::{cell::RefCell, rc::Rc};

pub struct FundSuccessHandler<
    R: ContractRuntimeContext + AccessControl + MemeRuntimeContext + ParametersInterface,
    S: StateInterface,
> {
    runtime: Rc<RefCell<R>>,
    state: Rc<RefCell<S>>,

    transfer_id: u64,
}

impl<R, S> FundSuccessHandler<R, S>
where
    R: ContractRuntimeContext + AccessControl + MemeRuntimeContext + ParametersInterface,
    S: StateInterface,
{
    pub fn new(runtime: Rc<RefCell<R>>, state: S, msg: &PoolMessage) -> Self {
        let PoolMessage::FundSuccess { transfer_id } = msg else {
            panic!("Invalid message");
        };

        Self {
            state: Rc::new(RefCell::new(state)),
            runtime,

            transfer_id: *transfer_id,
        }
    }

    async fn transfer_meme(&mut self, token: ApplicationId, to: Account, amount: Amount) {
        let _ = TransferMemeFromApplicationHandler::new(
            self.runtime.clone(),
            self.state.clone(),
            token,
            to,
            amount,
        )
        .handle()
        .await;
    }

    async fn transfer_meme_to_creation_chain_application(&mut self, fund_request: &FundRequest) {
        let application = self.runtime.borrow_mut().application_creation_account();
        self.transfer_meme(
            fund_request.token.unwrap(),
            application,
            fund_request.amount_in,
        )
        .await;
    }

    async fn swap_fund_success(
        &mut self,
        fund_request: &FundRequest,
    ) -> HandlerOutcome<PoolMessage> {
        // 1: Still on caller chain, need to fund creation chain firstly
        self.transfer_meme_to_creation_chain_application(fund_request)
            .await;

        // 2: Let creation chain do swap
        let token_0 = self.runtime.borrow_mut().token_0();

        let destination = self.runtime.borrow_mut().application_creator_chain_id();
        let mut outcome = HandlerOutcome::new();

        outcome.with_message(
            destination,
            PoolMessage::Swap {
                origin: fund_request.from,
                amount_0_in: if fund_request.token == Some(token_0) {
                    Some(fund_request.amount_in)
                } else {
                    None
                },
                amount_1_in: if fund_request.token == Some(token_0) {
                    None
                } else {
                    Some(fund_request.amount_in)
                },
                amount_0_out_min: if fund_request.token == Some(token_0) {
                    None
                } else {
                    fund_request.pair_token_amount_out_min
                },
                amount_1_out_min: if fund_request.token == Some(token_0) {
                    fund_request.pair_token_amount_out_min
                } else {
                    None
                },
                to: fund_request.to,
                block_timestamp: fund_request.block_timestamp,
            },
        );

        outcome
    }

    fn fund_pool_application_creation_chain(&mut self, amount: Amount) {
        let owner = self.runtime.borrow_mut().authenticated_signer().unwrap();
        let application = self.runtime.borrow_mut().application_creation_account();

        let owner_balance = self.runtime.borrow_mut().owner_balance(owner);
        let chain_balance = self.runtime.borrow_mut().chain_balance();

        let from_owner_balance = if amount <= owner_balance {
            amount
        } else {
            owner_balance
        };
        let from_chain_balance = if amount <= owner_balance {
            Amount::ZERO
        } else {
            amount.try_sub(owner_balance).expect("Invalid amount")
        };

        assert!(from_owner_balance <= owner_balance, "Insufficient balance");
        assert!(from_chain_balance <= chain_balance, "Insufficient balance");

        if from_owner_balance > Amount::ZERO {
            self.runtime
                .borrow_mut()
                .transfer(owner, application, from_owner_balance);
        }
        if from_chain_balance > Amount::ZERO {
            self.runtime.borrow_mut().transfer(
                AccountOwner::CHAIN,
                application,
                from_chain_balance,
            );
        }
    }

    async fn add_liquidity_fund_success(
        &mut self,
        fund_request: &FundRequest,
    ) -> Result<Option<HandlerOutcome<PoolMessage>>, HandlerError> {
        if let Some(transfer_id) = fund_request.next_request {
            let fund_request = self
                .state
                .borrow()
                .fund_request(transfer_id)
                .await
                .map_err(Into::into)?;
            if let Some(token_1) = fund_request.token {
                let mut handler = RequestMemeFundHandler::new(
                    self.runtime.clone(),
                    self.state.clone(),
                    token_1,
                    fund_request.amount_in,
                    transfer_id,
                );
                return handler.handle().await;
            }

            // Pair token is native token, fund pool chain
            let fund_request = self
                .state
                .borrow()
                .fund_request(transfer_id)
                .await
                .map_err(Into::into)?;
            self.fund_pool_application_creation_chain(fund_request.amount_in);
        }

        let fund_request_0 = if let Some(transfer_id) = fund_request.prev_request {
            &self
                .state
                .borrow()
                .fund_request(transfer_id)
                .await
                .map_err(Into::into)?
        } else {
            fund_request
        };
        let fund_request_1 = if let Some(transfer_id) = fund_request.next_request {
            &self
                .state
                .borrow()
                .fund_request(transfer_id)
                .await
                .map_err(Into::into)?
        } else {
            fund_request
        };

        self.transfer_meme_to_creation_chain_application(fund_request_0)
            .await;
        if let Some(_) = fund_request_1.token {
            self.transfer_meme_to_creation_chain_application(fund_request_1)
                .await;
        }

        let destination = self.runtime.borrow_mut().application_creator_chain_id();
        let mut outcome = HandlerOutcome::new();

        // Here both assets are transferred to pool successfully
        outcome.with_message(
            destination,
            PoolMessage::AddLiquidity {
                origin: fund_request_0.from,
                amount_0_in: fund_request_0.amount_in,
                amount_1_in: fund_request_1.amount_in,
                amount_0_out_min: fund_request_0.pair_token_amount_out_min,
                amount_1_out_min: fund_request_1.pair_token_amount_out_min,
                to: fund_request_0.to,
                block_timestamp: fund_request_0.block_timestamp,
            },
        );

        Ok(Some(outcome))
    }
}

#[async_trait(?Send)]
impl<R, S> Handler<PoolMessage> for FundSuccessHandler<R, S>
where
    R: ContractRuntimeContext + AccessControl + MemeRuntimeContext + ParametersInterface,
    S: StateInterface,
{
    async fn handle(&mut self) -> Result<Option<HandlerOutcome<PoolMessage>>, HandlerError> {
        let mut fund_request = self
            .state
            .borrow()
            .fund_request(self.transfer_id)
            .await
            .map_err(Into::into)?;

        fund_request.status = FundStatus::Success;
        self.state
            .borrow_mut()
            .update_fund_request(self.transfer_id, fund_request.clone())
            .await
            .map_err(Into::into)?;

        match fund_request.fund_type {
            FundType::Swap => Ok(Some(self.swap_fund_success(&fund_request).await)),
            FundType::AddLiquidity => Ok(self.add_liquidity_fund_success(&fund_request).await?),
        }
    }
}
