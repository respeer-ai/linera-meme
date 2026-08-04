use crate::interfaces::state::StateInterface;
use abi::{application_state_base::PublicStateBaseInterface, meme::MemeOperation};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::Account;
use runtime::interfaces::{access_control::AccessControl, contract::ContractRuntimeContext};
use std::{cell::RefCell, rc::Rc};

pub struct TransferOwnershipHandler<
    R: ContractRuntimeContext + AccessControl,
    S: StateInterface + PublicStateBaseInterface,
> {
    runtime: Rc<RefCell<R>>,
    _state: S,

    new_owner: Account,
}

impl<R: ContractRuntimeContext + AccessControl, S: StateInterface + PublicStateBaseInterface>
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
impl<R: ContractRuntimeContext + AccessControl, S: StateInterface + PublicStateBaseInterface>
    Handler<abi::meme::MemeMessage, abi::meme::MemeResponse> for TransferOwnershipHandler<R, S>
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<abi::meme::MemeMessage, abi::meme::MemeResponse>>, HandlerError>
    {
        let destination = self.runtime.borrow_mut().application_creator_chain_id();
        let owner = self.runtime.borrow_mut().authenticated_account();

        let mut outcome = HandlerOutcome::new();
        outcome.with_message(
            destination,
            abi::meme::MemeMessage::TransferOwnership {
                owner,
                new_owner: self.new_owner,
            },
            false,
        );

        Ok(Some(outcome))
    }
}
