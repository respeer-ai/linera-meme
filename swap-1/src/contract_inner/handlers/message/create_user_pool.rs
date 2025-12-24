use crate::{
    contract_inner::handlers::create_pool::CreatePoolHandler, interfaces::state::StateInterface,
};
use abi::swap::SwapMessage;
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::{Account, Amount, ApplicationId};
use runtime::interfaces::{
    access_control::AccessControl, contract::ContractRuntimeContext, meme::MemeRuntimeContext,
};
use std::{cell::RefCell, rc::Rc};

pub struct CreateUserPoolHandler<
    R: ContractRuntimeContext + AccessControl + MemeRuntimeContext,
    S: StateInterface,
> {
    runtime: Rc<RefCell<R>>,
    state: S,

    token_0: ApplicationId,
    token_1: Option<ApplicationId>,
    amount_0: Amount,
    amount_1: Amount,
    to: Option<Account>,
}

impl<R: ContractRuntimeContext + AccessControl + MemeRuntimeContext, S: StateInterface>
    CreateUserPoolHandler<R, S>
{
    pub fn new(runtime: Rc<RefCell<R>>, state: S, msg: &SwapMessage) -> Self {
        let SwapMessage::CreateUserPool {
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

            token_0: *token_0,
            token_1: *token_1,
            amount_0: *amount_0,
            amount_1: *amount_1,
            to: *to,
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl + MemeRuntimeContext, S: StateInterface>
    Handler<SwapMessage> for CreateUserPoolHandler<R, S>
{
    async fn handle(&mut self) -> Result<Option<HandlerOutcome<SwapMessage>>, HandlerError> {
        if let Some(_) = self
            .state
            .get_pool_exchangable(self.token_0, self.token_1)
            .await?
        {
            // TODO: refund fee budget
            panic!("Pool exists");
        }

        let token_0_creator_chain_id = self
            .runtime
            .borrow_mut()
            .token_creator_chain_id(self.token_0)?;
        let token_1_creator_chain_id = if let Some(token_1) = self.token_1 {
            Some(self.runtime.borrow_mut().token_creator_chain_id(token_1)?)
        } else {
            None
        };
        let creator = self.runtime.borrow_mut().message_signer_account();

        let handler = CreatePoolHandler::new(
            self.runtime,
            self.state,
            creator,
            self.token_0,
            self.token_1,
            self.amount_0,
            self.amount_1,
            false,
            self.to,
            None,
            true,
        );

        handler.handle().await
    }
}
