use crate::interfaces::state::StateInterface;
use abi::proxy::ProxyMessage;
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::Account;
use runtime::interfaces::{
    access_control::AccessControl, contract::ContractRuntimeContext, meme::MemeRuntimeContext,
};
use std::{cell::RefCell, rc::Rc};

pub struct DeregisterMinerHandler<
    R: ContractRuntimeContext + AccessControl + MemeRuntimeContext,
    S: StateInterface,
> {
    _runtime: Rc<RefCell<R>>,
    state: S,

    owner: Account,
}

impl<R: ContractRuntimeContext + AccessControl + MemeRuntimeContext, S: StateInterface>
    DeregisterMinerHandler<R, S>
{
    pub fn new(runtime: Rc<RefCell<R>>, state: S, msg: &ProxyMessage) -> Self {
        let ProxyMessage::DeregisterMiner { owner } = msg else {
            panic!("Invalid message");
        };

        Self {
            state,
            _runtime: runtime,

            owner: *owner,
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl + MemeRuntimeContext, S: StateInterface>
    Handler<ProxyMessage> for DeregisterMinerHandler<R, S>
{
    async fn handle(&mut self) -> Result<Option<HandlerOutcome<ProxyMessage>>, HandlerError> {
        self.state
            .deregister_miner(self.owner)
            .map_err(Into::into)?;

        Ok(None)
    }
}
