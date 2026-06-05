use crate::interfaces::state::StateInterface;
use abi::swap::pool::{FundRequest, PoolMessage, PoolResponse};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use runtime::interfaces::{
    access_control::AccessControl, contract::ContractRuntimeContext, meme::MemeRuntimeContext,
};
use std::{cell::RefCell, rc::Rc};

pub struct RequestMemeFundHandler<
    R: ContractRuntimeContext + AccessControl + MemeRuntimeContext,
    S: StateInterface,
> {
    runtime: Rc<RefCell<R>>,
    _state: Rc<RefCell<S>>,

    prev: Option<FundRequest>,
    request: FundRequest,
    next: Option<FundRequest>,
}

impl<R: ContractRuntimeContext + AccessControl + MemeRuntimeContext, S: StateInterface>
    RequestMemeFundHandler<R, S>
{
    pub fn new(
        runtime: Rc<RefCell<R>>,
        state: Rc<RefCell<S>>,
        prev: Option<FundRequest>,
        request: FundRequest,
        next: Option<FundRequest>,
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
    Handler<PoolMessage, PoolResponse> for RequestMemeFundHandler<R, S>
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
            PoolMessage::RequestFund {
                prev: self.prev.clone(),
                request: self.request.clone(),
                next: self.next.clone(),
            },
            false,
        );

        Ok(Some(outcome))
    }
}
