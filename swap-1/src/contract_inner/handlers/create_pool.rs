use crate::interfaces::state::StateInterface;
use abi::{policy::open_chain_fee_budget, swap::router::SwapMessage};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::{
    Account, Amount, ApplicationId, ApplicationPermissions, ChainId, Timestamp,
};
use runtime::interfaces::{
    access_control::AccessControl, contract::ContractRuntimeContext, meme::MemeRuntimeContext,
};
use std::{cell::RefCell, rc::Rc};

pub struct CreatePoolHandler<
    R: ContractRuntimeContext + AccessControl + MemeRuntimeContext,
    S: StateInterface,
> {
    runtime: Rc<RefCell<R>>,
    state: Rc<RefCell<S>>,

    creator: Account,
    token_0: ApplicationId,
    token_1: Option<ApplicationId>,
    amount_0: Amount,
    amount_1: Amount,
    virtual_liquidity: bool,
    to: Option<Account>,
    _deadline: Option<Timestamp>,
    user_pool: bool,
}

impl<R: ContractRuntimeContext + AccessControl + MemeRuntimeContext, S: StateInterface>
    CreatePoolHandler<R, S>
{
    pub fn new(
        runtime: Rc<RefCell<R>>,
        state: Rc<RefCell<S>>,
        creator: Account,
        token_0: ApplicationId,
        token_1: Option<ApplicationId>,
        amount_0: Amount,
        amount_1: Amount,
        virtual_liquidity: bool,
        to: Option<Account>,
        _deadline: Option<Timestamp>,
        user_pool: bool,
    ) -> Self {
        Self {
            state,
            runtime,

            creator,
            token_0,
            token_1,
            amount_0,
            amount_1,
            virtual_liquidity,
            to,
            _deadline,
            user_pool,
        }
    }

    fn create_child_chain(
        &mut self,
        token_0: ApplicationId,
        token_1: Option<ApplicationId>,
    ) -> Result<ChainId, HandlerError> {
        // It should allow router and meme applications
        let ownership = self.runtime.borrow_mut().chain_ownership();

        let router_application_id = self.runtime.borrow_mut().application_id().forget_abi();
        let mut application_ids = vec![token_0, router_application_id];
        if let Some(token_1) = token_1 {
            application_ids.push(token_1);
        }

        let permissions = ApplicationPermissions {
            execute_operations: Some(application_ids),
            mandatory_applications: vec![],
            close_chain: vec![router_application_id],
            change_application_permissions: vec![router_application_id],
            call_service_as_oracle: Some(vec![router_application_id]),
            make_http_requests: Some(vec![router_application_id]),
        };
        Ok(self
            .runtime
            .borrow_mut()
            .open_chain(ownership, permissions, open_chain_fee_budget()))
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl + MemeRuntimeContext, S: StateInterface>
    Handler<SwapMessage> for CreatePoolHandler<R, S>
{
    async fn handle(&mut self) -> Result<Option<HandlerOutcome<SwapMessage>>, HandlerError> {
        let pool_bytecode_id = self.state.borrow_mut().pool_bytecode_id();

        let destination = self.create_child_chain(self.token_0, self.token_1)?;

        self.state.borrow_mut().create_pool_chain(destination);

        let token_0_creator_chain_id = self
            .runtime
            .borrow_mut()
            .token_creator_chain_id(self.token_0)
            .expect("Failed: token creator chain id");
        let token_1_creator_chain_id = if let Some(token_1) = self.token_1 {
            Some(
                self.runtime
                    .borrow_mut()
                    .token_creator_chain_id(token_1)
                    .expect("Failed: token creator chain id"),
            )
        } else {
            None
        };

        let mut outcome = HandlerOutcome::new();

        outcome.with_message(
            destination,
            SwapMessage::CreatePool {
                creator: self.creator,
                pool_bytecode_id,
                token_0_creator_chain_id,
                token_0: self.token_0,
                token_1_creator_chain_id,
                token_1: self.token_1,
                amount_0: self.amount_0,
                amount_1: self.amount_1,
                virtual_initial_liquidity: self.virtual_liquidity,
                to: self.to,
                user_pool: self.user_pool,
            },
        );

        Ok(Some(outcome))
    }
}
