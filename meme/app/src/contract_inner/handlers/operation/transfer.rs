use crate::interfaces::state::StateInterface;
use abi::{application_state_base::PublicStateBaseInterface, meme::MemeOperation};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::{Account, Amount};
use runtime::interfaces::{access_control::AccessControl, contract::ContractRuntimeContext};
use std::{cell::RefCell, rc::Rc};

pub struct TransferHandler<
    R: ContractRuntimeContext + AccessControl,
    S: StateInterface + PublicStateBaseInterface,
> {
    runtime: Rc<RefCell<R>>,
    _state: S,
    to: Account,
    amount: Amount,
}

impl<R: ContractRuntimeContext + AccessControl, S: StateInterface + PublicStateBaseInterface>
    TransferHandler<R, S>
{
    pub fn new(runtime: Rc<RefCell<R>>, state: S, operation: &MemeOperation) -> Self {
        let MemeOperation::Transfer { to, amount } = operation else {
            panic!("Invalid operation");
        };

        Self {
            runtime,
            _state: state,
            to: *to,
            amount: *amount,
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl, S: StateInterface + PublicStateBaseInterface>
    Handler<abi::meme::MemeMessage, abi::meme::MemeResponse> for TransferHandler<R, S>
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<abi::meme::MemeMessage, abi::meme::MemeResponse>>, HandlerError>
    {
        let destination = self.runtime.borrow_mut().application_creator_chain_id();
        let from = self.runtime.borrow_mut().authenticated_account();

        let mut outcome = HandlerOutcome::new();
        outcome.with_message(
            destination,
            abi::meme::MemeMessage::Transfer {
                from,
                to: self.to,
                amount: self.amount,
            },
            false,
        );

        Ok(Some(outcome))
    }
}
