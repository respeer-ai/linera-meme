use crate::{
    contract_inner::handlers::create_pool::CreatePoolHandler, interfaces::state::StateInterface,
};
use abi::swap::{pool::BootstrapPolicy, router::{SwapMessage, SwapResponse}};
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
    state: Rc<RefCell<S>>,

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
            ..
        } = msg
        else {
            panic!("Invalid message");
        };

        Self {
            state: Rc::new(RefCell::new(state)),
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
    Handler<SwapMessage, SwapResponse> for CreateUserPoolHandler<R, S>
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<SwapMessage, SwapResponse>>, HandlerError> {
        // CreateUserPool is not a second public surface with looser semantics.
        // It is the internal continuation of a public CreatePool request that is
        // already constrained to two-sided real initial liquidity.
        //
        // token_0 remains a meme application id.
        // token_1 remains either:
        // - Some(meme application id)
        // - None for the native-token fact shape
        assert!(Some(self.token_0) != self.token_1, "Invalid token pair");
        assert!(self.amount_0 > Amount::ZERO, "Invalid amount_0");
        assert!(self.amount_1 > Amount::ZERO, "Invalid amount_1");

        if let Some(_) = self
            .state
            .borrow()
            .get_pool_exchangable(self.token_0, self.token_1)
            .await
            .expect("Failed: get pool exchangable")
        {
            // TODO: refund fee budget
            panic!("Pool exists");
        }

        let creator = self.runtime.borrow_mut().message_signer_account();

        let mut handler = CreatePoolHandler::new(
            self.runtime.clone(),
            self.state.clone(),
            creator,
            self.token_0,
            self.token_1,
            self.amount_0,
            self.amount_1,
            BootstrapPolicy::UserCreatePool,
            self.to,
            None,
        );

        handler.handle().await
    }
}
