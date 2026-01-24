use crate::interfaces::state::StateInterface;
use abi::meme::{MemeMessage, MemeResponse};
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
    _runtime: Rc<RefCell<R>>,
    state: Rc<RefCell<S>>,

    owner: Account,
    new_owner: Account,
}

impl<R: ContractRuntimeContext + AccessControl + MemeRuntimeContext, S: StateInterface>
    TransferOwnershipHandler<R, S>
{
    pub fn new(runtime: Rc<RefCell<R>>, state: Rc<RefCell<S>>, msg: &MemeMessage) -> Self {
        let MemeMessage::TransferOwnership { owner, new_owner } = msg else {
            panic!("Invalid message");
        };

        Self {
            state,
            _runtime: runtime,

            owner: *owner,
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
        self.state
            .borrow_mut()
            .transfer_ownership(self.owner, self.new_owner)
            .map_err(Into::into)?;

        Ok(None)
    }
}
