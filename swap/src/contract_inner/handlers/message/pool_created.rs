use crate::interfaces::state::StateInterface;
use abi::{
    meme::{MemeAbi, MemeOperation},
    swap::router::{SwapMessage, SwapResponse},
};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::{Account, AccountOwner, Amount, ApplicationId};
use runtime::interfaces::{access_control::AccessControl, contract::ContractRuntimeContext};
use std::{cell::RefCell, rc::Rc};

pub struct PoolCreatedHandler<R: ContractRuntimeContext + AccessControl, S: StateInterface> {
    runtime: Rc<RefCell<R>>,
    state: S,

    creator: Account,
    pool_application: Account,
    token_0: ApplicationId,
    token_1: Option<ApplicationId>,
    amount_0: Amount,
    amount_1: Amount,
    virtual_initial_liquidity: bool,
    to: Option<Account>,
    user_pool: bool,
}

impl<R: ContractRuntimeContext + AccessControl, S: StateInterface> PoolCreatedHandler<R, S> {
    pub fn new(runtime: Rc<RefCell<R>>, state: S, msg: &SwapMessage) -> Self {
        let SwapMessage::PoolCreated {
            creator,
            pool_application,
            token_0,
            token_1,
            amount_0,
            amount_1,
            virtual_initial_liquidity,
            to,
            user_pool,
        } = msg
        else {
            panic!("Invalid message");
        };

        Self {
            state,
            runtime,

            creator: *creator,
            pool_application: *pool_application,
            token_0: *token_0,
            token_1: *token_1,
            amount_0: *amount_0,
            amount_1: *amount_1,
            virtual_initial_liquidity: *virtual_initial_liquidity,
            to: *to,
            user_pool: *user_pool,
        }
    }
}

impl<R: ContractRuntimeContext + AccessControl, S: StateInterface> PoolCreatedHandler<R, S> {
    fn initial_pool_created(
        &mut self,
        pool_application: Account,
        token_0: ApplicationId,
        amount_0: Amount,
        amount_1: Amount,
        virtual_initial_liquidity: bool,
    ) {
        if !virtual_initial_liquidity {
            // This message may be authenticated by other user who is not the owner of swap
            // creation chain
            let application =
                AccountOwner::from(self.runtime.borrow_mut().application_id().forget_abi());
            self.runtime
                .borrow_mut()
                .transfer(application, pool_application, amount_1);
        }

        // TODO: only call from InitializeLiquidity could transfer from application
        let call = MemeOperation::InitializeLiquidity {
            to: pool_application,
            amount: amount_0,
        };
        let _ = self
            .runtime
            .borrow_mut()
            .call_application(token_0.with_abi::<MemeAbi>(), &call);
    }

    fn user_pool_created(
        &mut self,
        pool_application: Account,
        token_0: ApplicationId,
        token_1: Option<ApplicationId>,
        amount_0: Amount,
        amount_1: Amount,
        to: Option<Account>,
    ) -> SwapMessage {
        SwapMessage::UserPoolCreated {
            pool_application,
            token_0,
            token_1,
            amount_0,
            amount_1,
            to,
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl, S: StateInterface>
    Handler<SwapMessage, SwapResponse> for PoolCreatedHandler<R, S>
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<SwapMessage, SwapResponse>>, HandlerError> {
        log::info!("DEBUG MSG:SWAP: pool created ...");

        assert!(self.amount_1 > Amount::ZERO, "Invalid amount");
        assert!(self.amount_0 > Amount::ZERO, "Invalid amount");

        let outcome_message = if self.user_pool {
            Some(self.user_pool_created(
                self.pool_application,
                self.token_0,
                self.token_1,
                self.amount_0,
                self.amount_1,
                self.to,
            ))
        } else {
            self.initial_pool_created(
                self.pool_application,
                self.token_0,
                self.amount_0,
                self.amount_1,
                self.virtual_initial_liquidity,
            );
            None
        };

        let timestamp = self.runtime.borrow_mut().system_time();
        self.state
            .create_pool(
                self.creator,
                self.token_0,
                self.token_1,
                self.pool_application,
                timestamp,
            )
            .await
            .expect("Failed: create pool");

        if outcome_message.is_none() {
            return Ok(None);
        }

        let destination = self.creator.chain_id;
        let mut outcome = HandlerOutcome::new();

        outcome.with_message(destination, outcome_message.unwrap());

        Ok(Some(outcome))
    }
}
