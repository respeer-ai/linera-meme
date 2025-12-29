use crate::interfaces::state::StateInterface;
use abi::meme::{MemeMessage, MemeOperation, MemeResponse};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::{Account, AccountOwner, Amount};
use runtime::interfaces::{
    access_control::AccessControl, contract::ContractRuntimeContext, meme::MemeRuntimeContext,
};
use std::{cell::RefCell, rc::Rc};

pub struct TransferFromApplicationHandler<
    R: ContractRuntimeContext + AccessControl + MemeRuntimeContext,
    S: StateInterface,
> {
    runtime: Rc<RefCell<R>>,
    _state: S,

    to: Account,
    amount: Amount,
}

impl<R: ContractRuntimeContext + AccessControl + MemeRuntimeContext, S: StateInterface>
    TransferFromApplicationHandler<R, S>
{
    pub fn new(runtime: Rc<RefCell<R>>, state: S, op: &MemeOperation) -> Self {
        let MemeOperation::TransferFromApplication { to, amount } = op else {
            panic!("Invalid operation");
        };

        Self {
            _state: state,
            runtime,

            to: *to,
            amount: *amount,
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl + MemeRuntimeContext, S: StateInterface>
    Handler<MemeMessage, MemeResponse> for TransferFromApplicationHandler<R, S>
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<MemeMessage, MemeResponse>>, HandlerError> {
        let destination = self.runtime.borrow_mut().application_creator_chain_id();
        let mut outcome = HandlerOutcome::new();

        // TODO: check called from caller creator chain
        let caller_id = self.runtime.borrow_mut().authenticated_caller_id().unwrap();
        // TODO: use creator chain id if we can get it from runtime
        let chain_id = self.runtime.borrow_mut().chain_id();

        let caller = Account {
            chain_id,
            owner: AccountOwner::from(caller_id),
        };

        outcome.with_message(
            destination,
            MemeMessage::TransferFromApplication {
                caller,
                to: self.to,
                amount: self.amount,
            },
        );

        Ok(Some(outcome))
    }
}
