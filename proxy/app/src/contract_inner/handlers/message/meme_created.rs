use crate::interfaces::state::StateInterface;
use abi::proxy::{ProxyMessage, ProxyResponse};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::{ApplicationId, ChainId};
use runtime::interfaces::{
    access_control::AccessControl, contract::ContractRuntimeContext, meme::MemeRuntimeContext,
};
use std::{cell::RefCell, rc::Rc};

pub struct MemeCreatedHandler<
    R: ContractRuntimeContext + AccessControl + MemeRuntimeContext,
    S: StateInterface,
> {
    _runtime: Rc<RefCell<R>>,
    state: S,

    chain_id: ChainId,
    token: ApplicationId,
}

impl<R: ContractRuntimeContext + AccessControl + MemeRuntimeContext, S: StateInterface>
    MemeCreatedHandler<R, S>
{
    pub fn new(runtime: Rc<RefCell<R>>, state: S, msg: &ProxyMessage) -> Self {
        let ProxyMessage::MemeCreated { chain_id, token } = msg else {
            panic!("Invalid message");
        };

        Self {
            state,
            _runtime: runtime,

            chain_id: *chain_id,
            token: *token,
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl + MemeRuntimeContext, S: StateInterface>
    Handler<ProxyMessage, ProxyResponse> for MemeCreatedHandler<R, S>
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<ProxyMessage, ProxyResponse>>, HandlerError> {
        self.state
            .create_chain_token(self.chain_id, self.token)
            .await
            .map_err(Into::into)?;

        Ok(None)
    }
}
