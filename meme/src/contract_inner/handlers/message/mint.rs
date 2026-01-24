use crate::interfaces::state::StateInterface;
use abi::meme::{MemeMessage, MemeResponse};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::{Account, Amount};
use runtime::interfaces::{
    access_control::AccessControl, contract::ContractRuntimeContext, meme::MemeRuntimeContext,
};
use std::{cell::RefCell, rc::Rc};

pub struct MintHandler<
    R: ContractRuntimeContext + AccessControl + MemeRuntimeContext,
    S: StateInterface,
> {
    runtime: Rc<RefCell<R>>,
    state: Rc<RefCell<S>>,

    to: Account,
    amount: Amount,
}

impl<R: ContractRuntimeContext + AccessControl + MemeRuntimeContext, S: StateInterface>
    MintHandler<R, S>
{
    pub fn new(runtime: Rc<RefCell<R>>, state: Rc<RefCell<S>>, msg: &MemeMessage) -> Self {
        let MemeMessage::Mint { to, amount } = msg else {
            panic!("Invalid message");
        };

        Self {
            state,
            runtime,

            to: *to,
            amount: *amount,
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl + MemeRuntimeContext, S: StateInterface>
    Handler<MemeMessage, MemeResponse> for MintHandler<R, S>
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<MemeMessage, MemeResponse>>, HandlerError> {
        let signer = self.runtime.borrow_mut().authenticated_signer().unwrap();
        let owner = self.state.borrow().owner_signer();

        assert!(signer == owner, "Invalid caller");

        self.state
            .borrow_mut()
            .mint(self.to, self.amount)
            .await
            .map_err(Into::into)?;

        Ok(None)
    }
}
