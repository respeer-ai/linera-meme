use crate::interfaces::{parameters::ParametersInterface, state::StateInterface};
use abi::{
    meme::{MemeMessage, MemeResponse},
    proxy::{ProxyAbi, ProxyOperation, ProxyResponse},
};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::Amount;
use runtime::interfaces::{access_control::AccessControl, contract::ContractRuntimeContext};
use std::{cell::RefCell, rc::Rc};

pub struct OpenMultiLeaderRoundsHandler<
    R: ContractRuntimeContext + AccessControl + ParametersInterface,
    S: StateInterface,
> {
    runtime: Rc<RefCell<R>>,
    state: Rc<RefCell<S>>,
}

impl<R: ContractRuntimeContext + AccessControl + ParametersInterface, S: StateInterface>
    OpenMultiLeaderRoundsHandler<R, S>
{
    pub fn new(runtime: Rc<RefCell<R>>, state: Rc<RefCell<S>>) -> Self {
        Self { state, runtime }
    }

    fn should_open_multi_leader_rounds(&self) -> bool {
        let enable_mining = self.runtime.borrow_mut().enable_mining();
        let mining_supply = self.runtime.borrow_mut().mining_supply();

        enable_mining
            && matches!(
                mining_supply,
                Some(supply) if supply > Amount::ZERO
            )
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl + ParametersInterface, S: StateInterface>
    Handler<MemeMessage, MemeResponse> for OpenMultiLeaderRoundsHandler<R, S>
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<MemeMessage, MemeResponse>>, HandlerError> {
        if !self.should_open_multi_leader_rounds() {
            return Ok(None);
        }

        // We cannot change ownership by meme application, we need proxy to do it
        let call = ProxyOperation::OpenMultiLeaderRounds;
        let proxy_application_id = self
            .state
            .borrow()
            .proxy_application_id()
            .expect("Invalid proxy application");

        if ProxyResponse::Ok
            != self
                .runtime
                .borrow_mut()
                .call_application(proxy_application_id.with_abi::<ProxyAbi>(), &call)
        {
            return Err(HandlerError::RuntimeError(
                "Invalid application response".into(),
            ));
        }

        Ok(None)
    }
}
