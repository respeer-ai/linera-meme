use crate::{
    contract_inner::handlers::{
        refund::RefundHandler, transfer_meme_from_application::TransferMemeFromApplicationHandler,
    },
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

pub struct SwapHandler<
    R: ContractRuntimeContext + AccessControl + MemeRuntimeContext + ParametersInterface,
    S: StateInterface,
> {
    runtime: Rc<RefCell<R>>,
    state: Rc<RefCell<S>>,

    origin: Account,
    amount_0_in: Option<Amount>,
    amount_1_in: Option<Amount>,
    amount_0_out_min: Option<Amount>,
    amount_1_out_min: Option<Amount>,
    to: Option<Account>,
    block_timestamp: Option<Timestamp>,
}

impl<
        R: ContractRuntimeContext + AccessControl + MemeRuntimeContext + ParametersInterface,
        S: StateInterface,
    > SwapHandler<R, S>
{
    pub fn new(runtime: Rc<RefCell<R>>, state: S, msg: &PoolMessage) -> Self {
        let PoolMessage::Swap {
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

    async fn refund_amount_in(
        &mut self,
        origin: Account,
        amount_0_in: Option<Amount>,
        amount_1_in: Option<Amount>,
    ) {
        let _ = RefundHandler::new(
            self.runtime.clone(),
            self.state.clone(),
            origin,
            amount_0_in,
            amount_1_in,
        )
        .handle()
        .await;
    }

    // Always be run on creation chain
    async fn do_swap(
        &mut self,
        origin: Account,
        amount_0_in: Option<Amount>,
        amount_1_in: Option<Amount>,
        amount_0_out_min: Option<Amount>,
        amount_1_out_min: Option<Amount>,
        to: Option<Account>,
        _block_timestamp: Option<Timestamp>,
    ) -> Result<HandlerOutcome<PoolMessage>, HandlerError> {
        log::info!(
            "DEBUG POOL: Swapping token_0 {} amunt_0 {:?}/{:?} token_1 {:?} amount_1 {:?}/{:?}",
            self.runtime.borrow_mut().token_0(),
            amount_0_in,
            amount_0_out_min,
            self.runtime.borrow_mut().token_1(),
            amount_1_in,
            amount_1_out_min
        );

        // Here we already funded
        // 1: Calculate pair token amount
        let amount_0_out = if let Some(amount_1_in) = amount_1_in {
            self.state
                .borrow()
                .calculate_swap_amount_0(amount_1_in)
                .map_err(Into::into)?
        } else {
            Amount::ZERO
        };
        if let Some(amount_0_out_min) = amount_0_out_min {
            if amount_0_out < amount_0_out_min {
                self.refund_amount_in(origin, amount_0_in, amount_1_in)
                    .await;
                log::warn!(
                    "DEBUG POOL: Amount 0 out {} less than minimum {}",
                    amount_0_out,
                    amount_0_out_min
                );
                return Err(HandlerError::InvalidAmount);
            }
        }

        let amount_1_out = if let Some(amount_0_in) = amount_0_in {
            self.state
                .borrow()
                .calculate_swap_amount_1(amount_0_in)
                .map_err(Into::into)?
        } else {
            Amount::ZERO
        };
        if let Some(amount_1_out_min) = amount_1_out_min {
            if amount_1_out < amount_1_out_min {
                self.refund_amount_in(origin, amount_0_in, amount_1_in)
                    .await;
                log::warn!(
                    "DEBUG POOL: Amount 1 out {} less than minimum {}",
                    amount_1_out,
                    amount_1_out_min
                );
                return Err(HandlerError::InvalidAmount);
            }
        }

        if amount_0_in.unwrap_or(Amount::ZERO) > Amount::ZERO && amount_1_out == Amount::ZERO {
            self.refund_amount_in(origin, amount_0_in, amount_1_in)
                .await;
            log::warn!(
                "DEBUG POOL: Amount 0 in {:?} > 0 but amount 1 out {} is ZERO",
                amount_0_in,
                amount_1_out
            );
            return Err(HandlerError::InvalidAmount);
        }
        if amount_1_in.unwrap_or(Amount::ZERO) > Amount::ZERO && amount_0_out == Amount::ZERO {
            self.refund_amount_in(origin, amount_0_in, amount_1_in)
                .await;
            log::warn!(
                "DEBUG POOL: Amount 1 in {:?} > 0 but amount 0 out {} is ZERO",
                amount_1_in,
                amount_0_out
            );
            return Err(HandlerError::InvalidAmount);
        }
        if amount_0_out == Amount::ZERO && amount_1_out == Amount::ZERO {
            self.refund_amount_in(origin, amount_0_in, amount_1_in)
                .await;
            log::warn!("Both amount 0 and 1 out are ZERO");
            return Err(HandlerError::InvalidAmount);
        }

        // 2: Check liquidity
        log::info!(
            "DEBUG POOL: calculating adjusted amount pair ... amount 0 {}, amount 1 {}",
            amount_0_out,
            amount_1_out
        );

        let amount_pair = self
            .state
            .borrow()
            .calculate_adjusted_amount_pair(amount_0_out, amount_1_out);
        match amount_pair {
            Ok(_) => {}
            Err(err) => {
                self.refund_amount_in(origin, amount_0_in, amount_1_in)
                    .await;
                log::warn!(
                    "DEBUG POOL: Failed caculate adjusted amount pair amount 0 out {}, amount 1 out {}",
                    amount_0_out,
                    amount_1_out
                );
                return Err(err.into());
            }
        }

        // 3: Transfer token
        let to = to.unwrap_or(origin);
        let application =
            AccountOwner::from(self.runtime.borrow_mut().application_id().forget_abi());
        let token_0 = self.runtime.borrow_mut().token_0();

        log::info!(
            "DEBUG POOL: transferring tokens ... amount 0 {}, amount 1 {}",
            amount_0_out,
            amount_1_out
        );

        if amount_1_out > Amount::ZERO {
            let token_1 = self.runtime.borrow_mut().token_1();
            if let Some(token_1) = token_1 {
                log::info!(
                    "DEBUG POOL: transferring ... token {}, amount {}",
                    token_1,
                    amount_1_out
                );
                self.transfer_meme(token_1, to, amount_1_out).await;
            } else {
                let balance = self.runtime.borrow_mut().owner_balance(application);

                log::info!(
                    "DEBUG POOL: transferring ... token {:?}, amount {}, balance {}",
                    self.runtime.borrow_mut().token_1(),
                    amount_1_out,
                    balance
                );

                if balance < amount_1_out {
                    self.refund_amount_in(origin, amount_0_in, amount_1_in)
                        .await;
                    log::warn!(
                        "DEBUG POOL: Application balance {} less than amount 1 out {}",
                        balance,
                        amount_1_out
                    );
                    return Err(HandlerError::InsufficientFunds);
                }
                self.runtime
                    .borrow_mut()
                    .transfer(application, to, amount_1_out);
            }
        }
        // Transfer native firstly due to meme transfer is a message
        if amount_0_out > Amount::ZERO {
            log::info!(
                "DEBUG POOL: transferring ... token {}, amount {}",
                token_0,
                amount_0_out
            );
            self.transfer_meme(token_0, to, amount_0_out).await;
        }

        // 4: Liquid

        let balance_0 = self
            .state
            .borrow()
            .reserve_0()
            .try_sub(amount_0_out)
            .unwrap()
            .try_add(amount_0_in.unwrap_or(Amount::ZERO))
            .unwrap();
        let balance_1 = self
            .state
            .borrow()
            .reserve_1()
            .try_sub(amount_1_out)
            .unwrap()
            .try_add(amount_1_in.unwrap_or(Amount::ZERO))
            .unwrap();
        let timestamp = self.runtime.borrow_mut().system_time();

        log::info!(
            "DEBUG POOL: liquiding ... balance 0 {}, balance 1 {}",
            balance_0,
            balance_1
        );
        self.state
            .borrow_mut()
            .liquid(balance_0, balance_1, timestamp);

        let transaction = self.state.borrow().build_transaction(
            origin,
            amount_0_in,
            amount_1_in,
            if amount_0_out > Amount::ZERO {
                Some(amount_0_out)
            } else {
                None
            },
            if amount_1_out > Amount::ZERO {
                Some(amount_1_out)
            } else {
                None
            },
            None,
            timestamp,
        );
        // We already on creator chain
        let destination = self.runtime.borrow_mut().chain_id();
        let mut outcome = HandlerOutcome::new();

        outcome.with_message(destination, PoolMessage::NewTransaction { transaction });

        Ok(outcome)
    }
}

#[async_trait(?Send)]
impl<
        R: ContractRuntimeContext + AccessControl + MemeRuntimeContext + ParametersInterface,
        S: StateInterface,
    > Handler<PoolMessage> for SwapHandler<R, S>
{
    async fn handle(&mut self) -> Result<Option<HandlerOutcome<PoolMessage>>, HandlerError> {
        // We just return OK to refund the failed balance here
        match self
            .do_swap(
                self.origin,
                self.amount_0_in,
                self.amount_1_in,
                self.amount_0_out_min,
                self.amount_1_out_min,
                self.to,
                self.block_timestamp,
            )
            .await
        {
            Ok(outcome) => Ok(Some(outcome)),
            Err(err) => {
                log::warn!("Failed swap: {}", err);
                Ok(None)
            }
        }
    }
}
