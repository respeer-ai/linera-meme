use crate::interfaces::state::StateInterface;
use abi::proxy::{ProxyMessage, ProxyOperation, ProxyResponse};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::{ChainOwnership, TimeoutConfig};
use runtime::interfaces::{access_control::AccessControl, contract::ContractRuntimeContext};
use std::{cell::RefCell, rc::Rc};

pub struct OpenMultiLeaderRoundsHandler<
    R: ContractRuntimeContext + AccessControl,
    S: StateInterface,
> {
    runtime: Rc<RefCell<R>>,
    _state: S,
}

impl<R: ContractRuntimeContext + AccessControl, S: StateInterface>
    OpenMultiLeaderRoundsHandler<R, S>
{
    pub fn new(runtime: Rc<RefCell<R>>, state: S, op: &ProxyOperation) -> Self {
        let ProxyOperation::OpenMultiLeaderRounds = op else {
            panic!("Invalid operation");
        };

        Self {
            _state: state,
            runtime,
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl, S: StateInterface>
    Handler<ProxyMessage, ProxyResponse> for OpenMultiLeaderRoundsHandler<R, S>
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<ProxyMessage, ProxyResponse>>, HandlerError> {
        // When we're here, we already know it's minable meme
        // It's run on meme chain
        let mut ownership =
            ChainOwnership::multiple(Vec::new(), u32::MAX, TimeoutConfig::default());
        ownership.open_multi_leader_rounds = true;

        match self.runtime.borrow_mut().change_ownership(ownership) {
            Ok(_) => {}
            Err(e) => return Err(HandlerError::RuntimeError(e.into())),
        }

        Ok(None)
    }
}
