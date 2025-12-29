use crate::interfaces::state::StateInterface;
use abi::proxy::{ProxyMessage, ProxyOperation};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::Account;
use runtime::interfaces::{
    access_control::AccessControl, contract::ContractRuntimeContext, meme::MemeRuntimeContext,
};
use std::{cell::RefCell, rc::Rc};

pub struct ApproveAddGenesisMinerHandler<
    R: ContractRuntimeContext + AccessControl + MemeRuntimeContext,
    S: StateInterface,
> {
    runtime: Rc<RefCell<R>>,
    _state: S,

    owner: Account,
}

impl<R: ContractRuntimeContext + AccessControl + MemeRuntimeContext, S: StateInterface>
    ApproveAddGenesisMinerHandler<R, S>
{
    pub fn new(runtime: Rc<RefCell<R>>, state: S, op: &ProxyOperation) -> Self {
        let ProxyOperation::ApproveAddGenesisMiner { owner } = op else {
            panic!("Invalid operation");
        };

        Self {
            _state: state,
            runtime,

            owner: *owner,
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl + MemeRuntimeContext, S: StateInterface>
    Handler<ProxyMessage> for ApproveAddGenesisMinerHandler<R, S>
{
    async fn handle(&mut self) -> Result<Option<HandlerOutcome<ProxyMessage>>, HandlerError> {
        let destination = self.runtime.borrow_mut().application_creator_chain_id();
        let mut outcome = HandlerOutcome::new();

        let operator = self.runtime.borrow_mut().authenticated_account();

        outcome.with_message(
            destination,
            ProxyMessage::ApproveAddGenesisMiner {
                operator,
                owner: self.owner,
            },
        );

        Ok(Some(outcome))
    }
}
