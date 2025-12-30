use crate::{
    contract_inner::handlers::transfer_meme_from_application::TransferMemeFromApplicationHandler,
    interfaces::{parameters::ParametersInterface, state::StateInterface},
};
use abi::swap::pool::{PoolMessage, PoolResponse};
use async_trait::async_trait;
use base::handler::{Handler, HandlerError, HandlerOutcome};
use linera_sdk::linera_base_types::{Account, AccountOwner, Amount, ApplicationId};
use runtime::interfaces::{
    access_control::AccessControl, contract::ContractRuntimeContext, meme::MemeRuntimeContext,
};
use std::{cell::RefCell, rc::Rc};

pub struct RefundHandler<
    R: ContractRuntimeContext + AccessControl + MemeRuntimeContext + ParametersInterface,
    S: StateInterface,
> {
    runtime: Rc<RefCell<R>>,
    state: Rc<RefCell<S>>,

    origin: Account,
    amount_0: Option<Amount>,
    amount_1: Option<Amount>,
}

impl<
        R: ContractRuntimeContext + AccessControl + MemeRuntimeContext + ParametersInterface,
        S: StateInterface,
    > RefundHandler<R, S>
{
    pub fn new(
        runtime: Rc<RefCell<R>>,
        state: Rc<RefCell<S>>,
        origin: Account,
        amount_0: Option<Amount>,
        amount_1: Option<Amount>,
    ) -> Self {
        Self {
            state,
            runtime,

            origin,
            amount_0,
            amount_1,
        }
    }

    async fn transfer_meme(&mut self, token: ApplicationId, to: Account, amount: Amount) {
        let _ = TransferMemeFromApplicationHandler::new(
            self.runtime.clone(),
            self.state.clone(),
            token,
            to,
            amount,
        )
        .handle()
        .await;
    }
}

#[async_trait(?Send)]
impl<
        R: ContractRuntimeContext + AccessControl + MemeRuntimeContext + ParametersInterface,
        S: StateInterface,
    > Handler<PoolMessage, PoolResponse> for RefundHandler<R, S>
{
    async fn handle(
        &mut self,
    ) -> Result<Option<HandlerOutcome<PoolMessage, PoolResponse>>, HandlerError> {
        let amount_1_in = self.amount_1.unwrap_or(Amount::ZERO);
        if amount_1_in > Amount::ZERO {
            let token_1 = self.runtime.borrow_mut().token_1();
            if let Some(token_1) = token_1 {
                self.transfer_meme(token_1, self.origin, amount_1_in).await;
            } else {
                let application =
                    AccountOwner::from(self.runtime.borrow_mut().application_id().forget_abi());
                self.runtime
                    .borrow_mut()
                    .transfer(application, self.origin, amount_1_in);
            }
        }
        let amount_0_in = self.amount_0.unwrap_or(Amount::ZERO);
        let token_0 = self.runtime.borrow_mut().token_0();
        // Transfer native firstly due to meme transfer is a message
        if amount_0_in > Amount::ZERO {
            self.transfer_meme(token_0, self.origin, amount_0_in).await;
        }

        Ok(None)
    }
}
