use crate::interfaces::state::StateInterface;
use abi::meme::{MemeMessage, MemeOperation, MemeResponse};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::Account;
use runtime::interfaces::{
    access_control::AccessControl, contract::ContractRuntimeContext, meme::MemeRuntimeContext,
};
use std::{cell::RefCell, rc::Rc};

pub struct TransferOwnershipHandler<
    R: ContractRuntimeContext + AccessControl + MemeRuntimeContext,
    S: StateInterface,
> {
    runtime: Rc<RefCell<R>>,
    _state: S,

    new_owner: Account,
}

impl<R: ContractRuntimeContext + AccessControl + MemeRuntimeContext, S: StateInterface>
    TransferOwnershipHandler<R, S>
{
    pub fn new(runtime: Rc<RefCell<R>>, state: S, op: &MemeOperation) -> Self {
        let MemeOperation::TransferOwnership { new_owner } = op else {
            panic!("Invalid operation");
        };

        Self {
            _state: state,
            runtime,

            new_owner: *new_owner,
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl + MemeRuntimeContext, S: StateInterface>
    Handler<MemeMessage, MemeResponse> for TransferOwnershipHandler<R, S>
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<MemeMessage, MemeResponse>>, HandlerError> {
        let destination = self.runtime.borrow_mut().application_creator_chain_id();
        let mut outcome = HandlerOutcome::new();

        let owner = self.runtime.borrow_mut().authenticated_account();
        outcome.with_message(
            destination,
            MemeMessage::TransferOwnership {
                owner,
                new_owner: self.new_owner,
            },
        );

        Ok(Some(outcome))
    }
}
