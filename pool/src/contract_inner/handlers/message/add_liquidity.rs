use crate::{
    contract_inner::handlers::transfer_meme_from_application::TransferMemeFromApplicationHandler,
    interfaces::{parameters::ParametersInterface, state::StateInterface},
};
use abi::swap::pool::PoolMessage;
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::{Account, AccountOwner, Amount, ApplicationId, Timestamp};
use runtime::interfaces::{
    access_control::AccessControl, contract::ContractRuntimeContext, meme::MemeRuntimeContext,
};
use std::{cell::RefCell, rc::Rc};

pub struct AddLiquidityHandler<
    R: ContractRuntimeContext + AccessControl + ParametersInterface + MemeRuntimeContext,
    S: StateInterface,
> {
    runtime: Rc<RefCell<R>>,
    state: Rc<RefCell<S>>,

    origin: Account,
    amount_0_in: Amount,
    amount_1_in: Amount,
    amount_0_out_min: Option<Amount>,
    amount_1_out_min: Option<Amount>,
    to: Option<Account>,
    block_timestamp: Option<Timestamp>,
}

impl<
        R: ContractRuntimeContext + AccessControl + ParametersInterface + MemeRuntimeContext,
        S: StateInterface,
    > AddLiquidityHandler<R, S>
{
    pub fn new(runtime: Rc<RefCell<R>>, state: S, msg: &PoolMessage) -> Self {
        let PoolMessage::AddLiquidity {
            origin,
            amount_0_in,
            amount_1_in,
            amount_0_out_min,
            amount_1_out_min,
            to,
            block_timestamp,
        } = msg
        else {
            panic!("Invalid message");
        };

        Self {
            state: Rc::new(RefCell::new(state)),
            runtime,

            origin: *origin,
            amount_0_in: *amount_0_in,
            amount_1_in: *amount_1_in,
            amount_0_out_min: *amount_0_out_min,
            amount_1_out_min: *amount_1_out_min,
            to: *to,
            block_timestamp: *block_timestamp,
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
}

#[async_trait(?Send)]
impl<
        R: ContractRuntimeContext + AccessControl + ParametersInterface + MemeRuntimeContext,
        S: StateInterface,
    > Handler<PoolMessage> for AddLiquidityHandler<R, S>
{
    async fn handle(&mut self) -> Result<Option<HandlerOutcome<PoolMessage>>, HandlerError> {
        // We already receive all funds here
        let (amount_0, amount_1) = self
            .state
            .borrow()
            .try_calculate_swap_amount_pair(
                self.amount_0_in,
                self.amount_1_in,
                self.amount_0_out_min,
                self.amount_1_out_min,
            )
            .map_err(Into::into)?;

        let to = self.to.unwrap_or(self.origin);
        let timestamp = self.runtime.borrow_mut().system_time();
        let liquidity = self
            .state
            .borrow_mut()
            .add_liquidity(
                amount_0,
                amount_1,
                to,
                self.block_timestamp.unwrap_or(timestamp),
            )
            .await
            .map_err(Into::into)?;

        if self.amount_0_in > amount_0 {
            let token_0 = self.runtime.borrow_mut().token_0();
            self.transfer_meme(token_0, self.origin, self.amount_0_in.try_sub(amount_0)?)
                .await;
        }
        if self.amount_1_in > amount_1 {
            let token_1 = self.runtime.borrow_mut().token_1();
            match token_1 {
                Some(token_1) => {
                    self.transfer_meme(token_1, self.origin, self.amount_1_in.try_sub(amount_1)?)
                        .await;
                }
                None => {
                    let application =
                        AccountOwner::from(self.runtime.borrow_mut().application_id().forget_abi());
                    self.runtime.borrow_mut().transfer(
                        application,
                        self.origin,
                        self.amount_1_in.try_sub(amount_1)?,
                    )
                }
            };
        }

        let transaction = self.state.borrow().build_transaction(
            self.origin,
            Some(amount_0),
            Some(amount_1),
            None,
            None,
            Some(liquidity),
            self.block_timestamp.unwrap_or(timestamp),
        );

        let destination = self.runtime.borrow_mut().chain_id();
        let mut outcome = HandlerOutcome::new();

        outcome.with_message(destination, PoolMessage::NewTransaction { transaction });

        Ok(Some(outcome))
    }
}
