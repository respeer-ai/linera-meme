use crate::interfaces::state::StateInterface;
use abi::swap::{
    pool::{PoolAbi, PoolOperation},
    router::SwapMessage,
};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::{Account, AccountOwner, Amount, ApplicationId};
use runtime::interfaces::{access_control::AccessControl, contract::ContractRuntimeContext};
use std::{cell::RefCell, rc::Rc};

pub struct UserPoolCreatedHandler<R: ContractRuntimeContext + AccessControl, S: StateInterface> {
    runtime: Rc<RefCell<R>>,
    state: S,

    pool_application: Account,
    token_0: ApplicationId,
    token_1: Option<ApplicationId>,
    amount_0: Amount,
    amount_1: Amount,
    to: Option<Account>,
}

impl<R: ContractRuntimeContext + AccessControl, S: StateInterface> UserPoolCreatedHandler<R, S> {
    pub fn new(runtime: Rc<RefCell<R>>, state: S, msg: &SwapMessage) -> Self {
        let SwapMessage::UserPoolCreated {
            pool_application,
            token_0,
            token_1,
            amount_0,
            amount_1,
            to,
        } = msg
        else {
            panic!("Invalid message");
        };

        Self {
            state,
            runtime,

            pool_application: *pool_application,
            token_0: *token_0,
            token_1: *token_1,
            amount_0: *amount_0,
            amount_1: *amount_1,
            to: *to,
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl, S: StateInterface> Handler<SwapMessage>
    for UserPoolCreatedHandler<R, S>
{
    async fn handle(&mut self) -> Result<Option<HandlerOutcome<SwapMessage>>, HandlerError> {
        // Now we're on our caller chain, we can call all liquidity like what we do in out wallet
        let call = PoolOperation::AddLiquidity {
            amount_0_in: self.amount_0,
            amount_1_in: self.amount_1,
            amount_0_out_min: None,
            amount_1_out_min: None,
            to: self.to,
            block_timestamp: None,
        };
        let AccountOwner::Address32(application_description_hash) = self.pool_application.owner
        else {
            panic!("Invalid owner");
        };
        let application_id: ApplicationId = ApplicationId::new(application_description_hash);
        let _ = self
            .runtime
            .borrow_mut()
            .call_application(application_id.with_abi::<PoolAbi>(), &call);
        Ok(None)
    }
}
