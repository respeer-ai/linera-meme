use crate::interfaces::state::StateInterface;
use abi::proxy::ProxyMessage;
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::Account;
use runtime::interfaces::{
    access_control::AccessControl, contract::ContractRuntimeContext, meme::MemeRuntimeContext,
};
use std::{cell::RefCell, rc::Rc};

pub struct ProposeRemoveGenesisMinerHandler<
    R: ContractRuntimeContext + AccessControl + MemeRuntimeContext,
    S: StateInterface,
> {
    _runtime: Rc<RefCell<R>>,
    state: S,

    operator: Account,
    owner: Account,
}

impl<R, S> ProposeRemoveGenesisMinerHandler<R, S>
where
    R: ContractRuntimeContext + AccessControl + MemeRuntimeContext,
    S: StateInterface,
{
    pub fn new(runtime: Rc<RefCell<R>>, state: S, msg: &ProxyMessage) -> Self {
        let ProxyMessage::ProposeRemoveGenesisMiner { operator, owner } = msg else {
            panic!("Invalid message");
        };

        Self {
            state,
            _runtime: runtime,

            operator: *operator,
            owner: *owner,
        }
    }
}

#[async_trait(?Send)]
impl<R, S> Handler<ProxyMessage> for ProposeRemoveGenesisMinerHandler<R, S>
where
    R: ContractRuntimeContext + AccessControl + MemeRuntimeContext,
    S: StateInterface,
{
    async fn handle(&mut self) -> Result<Option<HandlerOutcome<ProxyMessage>>, HandlerError> {
        self.state
            .remove_genesis_miner(self.owner)
            .await
            .map_err(Into::into)?;
        self.state
            .validate_operator(self.operator)
            .await
            .map_err(Into::into)?;
        self.state
            .approve_remove_genesis_miner(self.owner, self.operator)
            .await
            .map_err(Into::into)?;

        Ok(None)
    }
}
