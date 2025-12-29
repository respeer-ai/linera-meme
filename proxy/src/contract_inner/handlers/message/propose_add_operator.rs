use crate::interfaces::state::StateInterface;
use abi::proxy::ProxyMessage;
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::Account;
use runtime::interfaces::{
    access_control::AccessControl, contract::ContractRuntimeContext, meme::MemeRuntimeContext,
};
use std::{cell::RefCell, rc::Rc};

pub struct ProposeAddOperatorHandler<
    R: ContractRuntimeContext + AccessControl + MemeRuntimeContext,
    S: StateInterface,
> {
    _runtime: Rc<RefCell<R>>,
    state: S,

    operator: Account,
    owner: Account,
}

impl<R: ContractRuntimeContext + AccessControl + MemeRuntimeContext, S: StateInterface>
    ProposeAddOperatorHandler<R, S>
{
    pub fn new(runtime: Rc<RefCell<R>>, state: S, msg: &ProxyMessage) -> Self {
        let ProxyMessage::ProposeAddOperator { operator, owner } = msg else {
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
impl<R: ContractRuntimeContext + AccessControl + MemeRuntimeContext, S: StateInterface>
    Handler<ProxyMessage> for ProposeAddOperatorHandler<R, S>
{
    async fn handle(&mut self) -> Result<Option<HandlerOutcome<ProxyMessage>>, HandlerError> {
        self.state
            .add_operator(self.owner)
            .await
            .map_err(Into::into)?;
        // Everybody can propose add genesis miner. If it's proposed by operator, approve it
        self.state
            .validate_operator(self.operator)
            .await
            .map_err(Into::into)?;
        self.state
            .approve_add_operator(self.owner, self.operator)
            .await
            .map_err(Into::into)?;

        Ok(None)
    }
}
