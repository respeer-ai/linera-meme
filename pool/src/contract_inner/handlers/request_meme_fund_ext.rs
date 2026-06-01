use crate::interfaces::state::StateInterface;
use abi::swap::pool::{FundRequestExt, PoolMessage, PoolResponse};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use runtime::interfaces::{
    access_control::AccessControl, contract::ContractRuntimeContext, meme::MemeRuntimeContext,
};
use std::{cell::RefCell, rc::Rc};

pub struct RequestMemeFundExtHandler<
    R: ContractRuntimeContext + AccessControl + MemeRuntimeContext,
    S: StateInterface,
> {
    runtime: Rc<RefCell<R>>,
    _state: Rc<RefCell<S>>,

    prev: Option<FundRequestExt>,
    request: FundRequestExt,
    next: Option<FundRequestExt>,
}

impl<R: ContractRuntimeContext + AccessControl + MemeRuntimeContext, S: StateInterface>
    RequestMemeFundExtHandler<R, S>
{
    pub fn new(
        runtime: Rc<RefCell<R>>,
        state: Rc<RefCell<S>>,
        prev: Option<FundRequestExt>,
        request: FundRequestExt,
        next: Option<FundRequestExt>,
    ) -> Self {
        Self {
            runtime,
            _state: state,
            prev,
            request,
            next,
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl + MemeRuntimeContext, S: StateInterface>
    Handler<PoolMessage, PoolResponse> for RequestMemeFundExtHandler<R, S>
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<PoolMessage, PoolResponse>>, HandlerError> {
        let token = self.request.token.expect("Invalid fund token");
        let destination = self
            .runtime
            .borrow_mut()
            .token_creator_chain_id(token)
            .expect("Failed: token creator chain id");

        let mut outcome = HandlerOutcome::new();
        outcome.with_message(
            destination,
            PoolMessage::RequestFundExt {
                prev: self.prev.clone(),
                request: self.request.clone(),
                next: self.next.clone(),
            },
            false,
        );

        Ok(Some(outcome))
    }
}
