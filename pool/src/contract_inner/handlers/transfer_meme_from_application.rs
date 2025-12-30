use crate::interfaces::state::StateInterface;
use abi::{
    meme::{MemeAbi, MemeOperation},
    swap::pool::{PoolMessage, PoolResponse},
};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::{Account, Amount, ApplicationId};
use runtime::interfaces::{
    access_control::AccessControl, contract::ContractRuntimeContext, meme::MemeRuntimeContext,
};
use std::{cell::RefCell, rc::Rc};

// Transfer meme from caller application to `to`

pub struct TransferMemeFromApplicationHandler<
    R: ContractRuntimeContext + AccessControl + MemeRuntimeContext,
    S: StateInterface,
> {
    runtime: Rc<RefCell<R>>,
    _state: Rc<RefCell<S>>,

    token: ApplicationId,
    to: Account,
    amount: Amount,
}

impl<R: ContractRuntimeContext + AccessControl + MemeRuntimeContext, S: StateInterface>
    TransferMemeFromApplicationHandler<R, S>
{
    pub fn new(
        runtime: Rc<RefCell<R>>,
        state: Rc<RefCell<S>>,
        token: ApplicationId,
        to: Account,
        amount: Amount,
    ) -> Self {
        Self {
            _state: state,
            runtime,

            token,
            to,
            amount,
        }
    }
}

#[async_trait(?Send)]
impl<R: ContractRuntimeContext + AccessControl + MemeRuntimeContext, S: StateInterface>
    Handler<PoolMessage, PoolResponse> for TransferMemeFromApplicationHandler<R, S>
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<PoolMessage, PoolResponse>>, HandlerError> {
        let call = MemeOperation::TransferFromApplication {
            to: self.to,
            amount: self.amount,
        };
        let _ = self
            .runtime
            .borrow_mut()
            .call_application(self.token.with_abi::<MemeAbi>(), &call);

        Ok(None)
    }
}
