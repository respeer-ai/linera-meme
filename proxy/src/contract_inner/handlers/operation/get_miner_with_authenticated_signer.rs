use crate::interfaces::state::StateInterface;
use abi::proxy::{ProxyMessage, ProxyOperation, ProxyResponse};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use runtime::interfaces::{
    access_control::AccessControl, contract::ContractRuntimeContext, meme::MemeRuntimeContext,
};
use std::{cell::RefCell, rc::Rc};

pub struct GetMinerWithAuthenticatedSignerHandler<
    R: ContractRuntimeContext + AccessControl + MemeRuntimeContext,
    S: StateInterface,
> {
    runtime: Rc<RefCell<R>>,
    state: S,
}

impl<R: ContractRuntimeContext + AccessControl + MemeRuntimeContext, S: StateInterface>
    GetMinerWithAuthenticatedSignerHandler<R, S>
{
    pub fn new(runtime: Rc<RefCell<R>>, state: S, op: &ProxyOperation) -> Self {
        let ProxyOperation::GetMinerWithAuthenticatedSigner = op else {
            panic!("Invalid operation");
        };

        Self { state, runtime }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl + MemeRuntimeContext, S: StateInterface>
    Handler<ProxyMessage, ProxyResponse> for GetMinerWithAuthenticatedSignerHandler<R, S>
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<ProxyMessage, ProxyResponse>>, HandlerError> {
        let mut outcome = HandlerOutcome::new();

        let owner = self
            .runtime
            .borrow_mut()
            .authenticated_signer()
            .expect("Invalid signer");
        let miner = self
            .state
            .get_miner_with_account_owner(owner)
            .await
            .map_err(Into::into)?;

        outcome.with_response(ProxyResponse::Miner(miner));

        Ok(Some(outcome))
    }
}
