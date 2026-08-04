use crate::interfaces::state::StateInterface;
use abi::{application_state_base::PublicStateBaseInterface, meme::MemeOperation};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::{Account, AccountOwner, Amount};
use runtime::interfaces::{access_control::AccessControl, contract::ContractRuntimeContext};
use std::{cell::RefCell, rc::Rc};

pub struct TransferFromApplicationHandler<
    R: ContractRuntimeContext + AccessControl,
    S: StateInterface + PublicStateBaseInterface,
> {
    runtime: Rc<RefCell<R>>,
    _state: S,
    to: Account,
    amount: Amount,
}

impl<R: ContractRuntimeContext + AccessControl, S: StateInterface + PublicStateBaseInterface>
    TransferFromApplicationHandler<R, S>
{
    pub fn new(runtime: Rc<RefCell<R>>, state: S, operation: &MemeOperation) -> Self {
        let MemeOperation::TransferFromApplication { to, amount } = operation else {
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
    Handler<abi::meme::MemeMessage, abi::meme::MemeResponse>
    for TransferFromApplicationHandler<R, S>
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<abi::meme::MemeMessage, abi::meme::MemeResponse>>, HandlerError>
    {
        let destination = self.runtime.borrow_mut().application_creator_chain_id();
        let caller_id = self.runtime.borrow_mut().authenticated_caller_id().unwrap();
        let chain_id = self.runtime.borrow_mut().chain_id();
        let caller = Account {
            chain_id,
            owner: AccountOwner::from(caller_id),
        };

        let mut outcome = HandlerOutcome::new();
        outcome.with_message(
            destination,
            abi::meme::MemeMessage::TransferFromApplication {
                caller,
                to: self.to,
                amount: self.amount,
            },
            false,
        );

        Ok(Some(outcome))
    }
}
